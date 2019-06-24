import pytest

import json

from copy import deepcopy

from io import BytesIO

from vc2_conformance import bitstream
from vc2_conformance import tables

from vc2_conformance.state import State

from vc2_conformance import decoder

from vc2_conformance.scripts.vc2_bitstream_generator import (
    remove_comments_from_json,
    SmartSerialiser,
    NoAutomaticValueAvailableError,
    main,
)


class TestRemoveCommentsFromJSON(object):
    
    @pytest.mark.parametrize("value", [
        # Numbers
        123,
        1.23,
        # Booleans
        True,
        False,
        # Null
        None,
        # Empty array
        [],
        # No comments in array
        [False, 1, "two", ["Three", 4], {"five": 6}],
        # Empty object
        {},
        # No comments in object
        {"one": False, "two": 1, "three": "four", "five": [6], "seven": {"eight": 9}},
    ])
    def test_no_comment(self, value):
        value_before = deepcopy(value)
        remove_comments_from_json(value)
        assert value_before == value
    
    @pytest.mark.parametrize("array,comment_index", [
        # Start
        (["# Comment", False, 1, "two", [], {}], 0),
        # Middle
        ([False, "# Comment", 1, "two", [], {}], 1),
        # End
        ([False, 1, "two", [], {}, "# Comment"], 5),
    ])
    def test_removes_comment_in_array(self, array, comment_index):
        expected_array = deepcopy(array)
        del expected_array[comment_index]
        remove_comments_from_json(array)
        assert array == expected_array
    
    def test_removes_comment_in_object(self):
        object = {
            "#": "Comment",
            "one": True,
            "two": 2,
            "three": "3",
            "four": [],
            "five": {},
        }
        expected_object = deepcopy(object)
        del expected_object["#"]
        
        remove_comments_from_json(object)
        assert object == expected_object
    
    def test_recurses(self):
        object = {
            "#": "Comment",
            "one": ["# Comment", 123],
            "two": {"#": "Comment", "three": 123},
        }
        expected_object = {
            "one": [123],
            "two": {"three": 123},
        }
        
        remove_comments_from_json(object)
        assert object == expected_object


class TestSmartSerialiser(object):
    
    @pytest.fixture
    def f(self):
        return BytesIO()
    
    @pytest.fixture
    def w(self, f):
        return bitstream.BitstreamWriter(f)
    
    def test_remember_last_value_as_default(self, f, w):
        default_values = {dict: {"a": 0xAA, "b": 0xBB}}
        context = {
            # Should use default from the beginning as usual if no values
            # present
            "a": [],
            # Should use last used value as default
            "b": [0xB0, 0xB1],
        }
        with SmartSerialiser(w, context, default_values) as ser:
            ser.declare_list("a")
            ser.uint_lit("a", 1)
            ser.uint_lit("a", 1)
            ser.uint_lit("a", 1)
            
            ser.declare_list("b")
            ser.uint_lit("b", 1)
            ser.uint_lit("b", 1)
            ser.uint_lit("b", 1)
        w.flush()
        
        assert f.getvalue() == b"\xAA\xAA\xAA\xB0\xB1\xB1"
    
    @pytest.mark.parametrize("value_in,exp_bytes", [
        # Non-string
        (0xAB, b"\xAB"),
        # Simple expression
        ("0x80 + 0x09", b"\x89"),
        # Named constant from tables
        ("ParseCodes.end_of_sequence", b"\x10"),
        # Expression using vc2_math
        ("intlog2(1023)", b"\x0A"),
    ])
    @pytest.mark.parametrize("as_default", [False, True])
    def test_evaluate_strings_as_python(self, f, w, value_in, exp_bytes, as_default):
        if as_default:
            # Value passed in as default
            default_values = {dict: {"x": value_in}}
            context = {}
        else:
            # Value passed in as value
            default_values = {}
            context = {"x": value_in}
        
        with SmartSerialiser(w, context, default_values) as ser:
            ser.uint_lit("x", 1)
        w.flush()
        
        assert f.getvalue() == exp_bytes
    
    @pytest.mark.parametrize("value_in", [
        # As minimal expression
        "AUTO",
        # Returned by expression
        "[AUTO][0]",
    ])
    @pytest.mark.parametrize("as_default", [False, True])
    def test_evaluate_strings_to_auto_call(self, f, w, value_in, as_default):
        if as_default:
            # Value passed in as default
            default_values = {dict: {"x": value_in}}
            context = {}
        else:
            # Value passed in as value
            default_values = {}
            context = {"x": value_in}
        
        with SmartSerialiser(w, context, default_values) as ser:
            with pytest.raises(NoAutomaticValueAvailableError) as exc_info:
                ser.uint_lit("x", 1)
        
        assert exc_info.value.args == ("dict['x']", )
    
    def test_parse_info_offset_logging(self, w):
        context = bitstream.Sequence(data_units=[
            bitstream.DataUnit(
                parse_info=bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.padding_data,
                    next_parse_offset=tables.PARSE_INFO_HEADER_BYTES + 10,
                ),
            ),
            bitstream.DataUnit(
                parse_info=bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.padding_data,
                    next_parse_offset=tables.PARSE_INFO_HEADER_BYTES + 20,
                ),
            ),
            bitstream.DataUnit(
                parse_info=bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.end_of_sequence,
                ),
            ),
        ])
        with SmartSerialiser(w, context, bitstream.vc2_default_values) as ser:
            bitstream.parse_sequence(ser, State())
        
        assert ser._parse_info_offsets == [
            0,
            tables.PARSE_INFO_HEADER_BYTES + 10,
            tables.PARSE_INFO_HEADER_BYTES + 10 + tables.PARSE_INFO_HEADER_BYTES + 20,
        ]
    
    def test_auto_parse_info_offsets(self, f, w):
        context = bitstream.Sequence(data_units=[
            bitstream.DataUnit(
                parse_info=bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.padding_data,
                    next_parse_offset="AUTO",
                    previous_parse_offset="AUTO",
                ),
                padding=bitstream.Padding(
                    bytes=b"\xAA\xBB",
                )
            ),
            bitstream.DataUnit(
                parse_info=bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.auxiliary_data,
                    next_parse_offset="AUTO",
                    previous_parse_offset="AUTO",
                ),
                auxiliary_data=bitstream.AuxiliaryData(
                    bytes=b"\xAA\xBB\xCC\xDD",
                )
            ),
            bitstream.DataUnit(
                parse_info=bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.sequence_header,
                    next_parse_offset="AUTO",
                    previous_parse_offset="AUTO",
                ),
            ),
            bitstream.DataUnit(
                parse_info=bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.end_of_sequence,
                    next_parse_offset="AUTO",
                    previous_parse_offset="AUTO",
                ),
            ),
        ])
        with SmartSerialiser(w, context, bitstream.vc2_default_values) as ser:
            bitstream.parse_sequence(ser, State())
        w.flush()
        write_end_offset = w.tell()
        
        # Deserialise the stream again to check the parse info offsets
        f.seek(0)
        r = bitstream.BitstreamReader(f)
        with bitstream.Deserialiser(r) as des:
            bitstream.parse_sequence(des, State())
        assert r.tell() == write_end_offset
        
        for i, (exp_next, exp_prev) in enumerate([
            (tables.PARSE_INFO_HEADER_BYTES + 2, 0),
            (tables.PARSE_INFO_HEADER_BYTES + 4, tables.PARSE_INFO_HEADER_BYTES + 2),
            (16, tables.PARSE_INFO_HEADER_BYTES + 4),
            (0, 16),
        ]):
            parse_info = des.context["data_units"][i]["parse_info"]
            print(i)
            assert parse_info["next_parse_offset"] == exp_next
            assert parse_info["previous_parse_offset"] == exp_prev
    
    
    def test_auto_picture_number(self, f, w):
        context = bitstream.Sequence(data_units=[
            bitstream.DataUnit(
                parse_info=bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.sequence_header,
                ),
                sequence_header=bitstream.SequenceHeader(
                    video_parameters=bitstream.SourceParameters(
                        # Avoid creating large frames in test cases
                        frame_size=bitstream.FrameSize(
                            custom_dimensions_flag=True,
                            frame_width=4,
                            frame_height=4,
                        ),
                    ),
                ),
            ),
            bitstream.DataUnit(
                parse_info=bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.high_quality_picture,
                ),
                picture_parse=bitstream.PictureParse(
                    picture_header=bitstream.PictureHeader(
                        picture_number=0xFFFFFFFE,
                    ),
                ),
            ),
            bitstream.DataUnit(
                parse_info=bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.high_quality_picture_fragment,
                ),
                fragment_parse=bitstream.FragmentParse(
                    fragment_header=bitstream.FragmentHeader(
                        picture_number="AUTO",
                        fragment_slice_count=0,
                    ),
                ),
            ),
            bitstream.DataUnit(
                parse_info=bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.high_quality_picture_fragment,
                ),
                fragment_parse=bitstream.FragmentParse(
                    fragment_header=bitstream.FragmentHeader(
                        picture_number="AUTO",
                        fragment_slice_count=1,
                    ),
                ),
            ),
            bitstream.DataUnit(
                parse_info=bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.high_quality_picture,
                ),
                picture_parse=bitstream.PictureParse(
                    picture_header=bitstream.PictureHeader(
                        picture_number="AUTO",
                    ),
                ),
            ),
            bitstream.DataUnit(
                parse_info=bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.end_of_sequence,
                    next_parse_offset="AUTO",
                    previous_parse_offset="AUTO",
                ),
            ),
        ])
        with SmartSerialiser(w, context, bitstream.vc2_default_values) as ser:
            bitstream.parse_sequence(ser, State())
        w.flush()
        write_end_offset = w.tell()
        
        # Deserialise the stream again to check the picture numbers
        f.seek(0)
        r = bitstream.BitstreamReader(f)
        with bitstream.Deserialiser(r) as des:
            bitstream.parse_sequence(des, State())
        assert r.tell() == write_end_offset
        
        for i, type, exp_picture_number in [
            (1, "picture", 0xFFFFFFFE),
            (2, "fragment", 0xFFFFFFFF),
            (3, "fragment", 0xFFFFFFFF),  # Non-first fragment shouldn't increment
            (4, "picture", 0),
        ]:
            pic_or_frag_parse = des.context["data_units"][i]["{}_parse".format(type)]
            header = pic_or_frag_parse["{}_header".format(type)]
            assert header["picture_number"] == exp_picture_number


class TestMain(object):

    def test_integration(self, tmpdir):
        # An integration test of all essential features including:
        #
        # * Comments in the JSON
        # * Evaluating Python in strings
        # * 'AUTO' is given as the default value in appropriate places
        # * Fields populated by 'AUTO' produce valid bitstreams
        #
        # This test works by generating a bitstream and then passing it through
        # the VC-2 bitstream validator.
        
        spec_filename = str(tmpdir.join("spec.json"))
        bitstream_filename = str(tmpdir.join("out.vc2"))
        
        with open(spec_filename, "w") as f:
            json.dump({
                "data_units": [
                    {
                        "parse_info": {
                            "parse_code": "ParseCodes.sequence_header",
                        },
                        "sequence_header": {
                            "video_parameters": {
                                "#": "Use a smaller picture size to make serialisation faster.",
                                "frame_size": {
                                    "custom_dimensions_flag": True,
                                    "frame_width": 4,
                                    "frame_height": 4,
                                },
                                "clean_area": {
                                    "custom_clean_area_flag": True,
                                    "clean_width": 4,
                                    "clean_height": 4,
                                    "left_offset": 0,
                                    "top_offset": 0,
                                },
                            },
                        },
                    },
                    "# An example picture (picture numbers should be automatic)",
                    {
                        "parse_info": {
                            "parse_code": "ParseCodes.high_quality_picture",
                        },
                    },
                    "# An example fragmented picture",
                    {
                        "parse_info": {
                            "parse_code": "ParseCodes.high_quality_picture_fragment",
                        },
                        "fragment_parse": {
                            "fragment_header": {
                                "fragment_slice_count": 0,
                            },
                            "transform_parameters": {
                                "slice_parameters": {
                                    "slices_x": 1,
                                    "slices_y": 1,
                                },
                            },
                        }
                    },
                    {
                        "parse_info": {
                            "parse_code": "ParseCodes.high_quality_picture_fragment",
                        },
                        "fragment_parse": {
                            "fragment_header": {
                                "fragment_slice_count": 1,
                            }
                        }
                    },
                    "# A further two non-fragmented pictures (checks auto-numbering)",
                    {
                        "parse_info": {
                            "parse_code": "ParseCodes.high_quality_picture",
                        },
                    },
                    {
                        "parse_info": {
                            "parse_code": "ParseCodes.high_quality_picture",
                        },
                    },
                    "# That's all!",
                    {
                        "parse_info": {
                            "parse_code": "ParseCodes.end_of_sequence",
                        },
                    },
                ],
            }, f)
        
        # Should successfully generate a bitstream
        assert main([spec_filename, bitstream_filename]) == 0
        
        # Should successfully pass verification
        with open(bitstream_filename, "rb") as f:
            state = State()
            decoder.init_io(state, f)
            decoder.parse_sequence(state)
    
    def test_bad_specification_file(self, tmpdir, capsys):
        spec_filename = str(tmpdir.join("spec.json"))
        bitstream_filename = str(tmpdir.join("out.vc2"))
        
        assert main([spec_filename, bitstream_filename]) != 0
        
        assert capsys.readouterr()[1].startswith("Could not open")
    
    def test_bad_specification_json(self, tmpdir, capsys):
        spec_filename = str(tmpdir.join("spec.json"))
        bitstream_filename = str(tmpdir.join("out.vc2"))
        
        with open(spec_filename, "w") as f:
            f.write("oops")
        
        assert main([spec_filename, bitstream_filename]) != 0
        
        assert capsys.readouterr()[1].startswith("Invalid JSON")
    
    @pytest.mark.parametrize("value", [
        # Number
        123,
        1.23,
        # Bool
        True,
        False,
        # String
        "foobar",
        # Array
        [],
    ])
    def test_json_root_object_isnt_dict(self, value, tmpdir, capsys):
        spec_filename = str(tmpdir.join("spec.json"))
        bitstream_filename = str(tmpdir.join("out.vc2"))
        
        with open(spec_filename, "w") as f:
            json.dump(value, f)
        
        assert main([spec_filename, bitstream_filename]) != 0
        
        assert capsys.readouterr()[1].startswith("Specification must contain a JSON object")

    def test_missing_end_of_sequence(self, tmpdir, capsys):
        # Note that if the missing end of sequence is not detected the
        # serialiser will be stuck in an infinite loop generating default data
        # units.
        
        spec_filename = str(tmpdir.join("spec.json"))
        bitstream_filename = str(tmpdir.join("out.vc2"))
        
        with open(spec_filename, "w") as f:
            json.dump({}, f)
        
        assert main([spec_filename, bitstream_filename]) != 0
        
        assert capsys.readouterr()[1].startswith("Empty 'parse info' specification")

    def test_disallowed_field(self, tmpdir, capsys):
        spec_filename = str(tmpdir.join("spec.json"))
        bitstream_filename = str(tmpdir.join("out.vc2"))
        
        with open(spec_filename, "w") as f:
            json.dump({
                "data_units": [
                    {"parse_info": {"parse_code": "ParseCodes.end_of_sequence"}},
                ],
                "bad_entry": "oops",
            }, f)
        
        assert main([spec_filename, bitstream_filename]) != 0
        
        assert capsys.readouterr()[1] == (
            "The field 'bad_entry' is not allowed in dict "
            "(allowed fields: 'data_units', '_state')\n"
        )
    
    def test_unused_field(self, tmpdir, capsys):
        spec_filename = str(tmpdir.join("spec.json"))
        bitstream_filename = str(tmpdir.join("out.vc2"))
        
        with open(spec_filename, "w") as f:
            json.dump({
                "data_units": [
                    {
                        "parse_info": {
                            "parse_code": "ParseCodes.end_of_sequence",
                        },
                        "picture_parse": {},
                    },
                ],
            }, f)
        
        assert main([spec_filename, bitstream_filename]) != 0
        
        assert capsys.readouterr()[1] == (
            "Unused field Sequence['data_units'][0]['picture_parse']\n"
        )
    
    def test_bad_python_eval(self, tmpdir, capsys):
        spec_filename = str(tmpdir.join("spec.json"))
        bitstream_filename = str(tmpdir.join("out.vc2"))
        
        with open(spec_filename, "w") as f:
            json.dump({
                "data_units": [
                    {
                        "parse_info": {
                            "parse_code": "ParseCodes.oopsie",
                        },
                    },
                ],
            }, f)
        
        assert main([spec_filename, bitstream_filename]) != 0
        
        assert capsys.readouterr()[1] == (
            "Error evaluating 'ParseCodes.oopsie' in "
            "Sequence['data_units'][0]['parse_info']['parse_code']: "
            "AttributeError: oopsie\n"
        )
    
    def test_vc2_pseudocode_error(self, tmpdir, capsys):
        spec_filename = str(tmpdir.join("spec.json"))
        bitstream_filename = str(tmpdir.join("out.vc2"))
        
        # Picture without sequence header will fail to serialise
        with open(spec_filename, "w") as f:
            json.dump({
                "data_units": [
                    {
                        "parse_info": {
                            "parse_code": "ParseCodes.high_quality_picture",
                        },
                    },
                ],
            }, f)
        
        assert main([spec_filename, bitstream_filename]) != 0
        
        assert capsys.readouterr()[1] == (
            "Unable to construct bitstream at "
            "Sequence['data_units'][0]['picture_parse']['wavelet_transform']['transform_parameters']: "
            "KeyError: 'major_version' "
            "(is a sequence or fragment header missing?)\n"
        )
