import pytest

import json

import re

from copy import deepcopy

from io import BytesIO

from vc2_conformance import bitstream

import vc2_data_tables as tables

from vc2_conformance.state import State

from vc2_conformance import decoder

from vc2_conformance.scripts.vc2_bitstream_generator import (
    remove_comments_from_json,
    evaluate_strings_in_json,
    JSONEvalError,
    main,
)


class TestRemoveCommentsFromJSON(object):
    @pytest.mark.parametrize(
        "value",
        [
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
            {
                "one": False,
                "two": 1,
                "three": "four",
                "five": [6],
                "seven": {"eight": 9},
            },
        ],
    )
    def test_no_comment(self, value):
        value_before = deepcopy(value)
        remove_comments_from_json(value)
        assert value_before == value

    @pytest.mark.parametrize(
        "array,comment_index",
        [
            # Start
            (["# Comment", False, 1, "two", [], {}], 0),
            ([u"# Comment", False, 1, "two", [], {}], 0),
            # Middle
            ([False, "# Comment", 1, "two", [], {}], 1),
            ([False, u"# Comment", 1, "two", [], {}], 1),
            # End
            ([False, 1, "two", [], {}, "# Comment"], 5),
            ([False, 1, "two", [], {}, u"# Comment"], 5),
        ],
    )
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


class TestEvaluateStringsInJSON(object):
    @pytest.mark.parametrize(
        "value",
        [
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
            # No strings in array
            [False, 1, None, {}, []],
            # Empty object
            {},
            # No strings in object
            {"one": False, "two": 1, "three": {}, "four": []},
        ],
    )
    def test_no_strings(self, value):
        value_before = deepcopy(value)
        assert evaluate_strings_in_json(value) == value_before

    @pytest.mark.parametrize(
        "value,exp_value",
        [
            # Naked string
            ("x + 100", 200),
            (u"x + 100", 200),
            # String in array
            ([1, "x + 100", 3], [1, 200, 3]),
            ([1, u"x + 100", 3], [1, 200, 3]),
            # String in object
            ({"x*2": "x*2"}, {"x*2": 200}),
            ({"x*2": u"x*2"}, {"x*2": 200}),
        ],
    )
    def test_evaluates_string(self, value, exp_value):
        assert evaluate_strings_in_json(value, {"x": 100}) == exp_value

    def test_error(self):
        with pytest.raises(JSONEvalError) as exc_info:
            evaluate_strings_in_json({"foo": [1, "1 / 0", 3]})

        assert str(exc_info.value).startswith(
            "Evaluation of '1 / 0' in Sequence['foo'][1] failed: " "ZeroDivisionError:"
        )


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
            json.dump(
                {
                    "data_units": [
                        {
                            "parse_info": {"parse_code": "ParseCodes.sequence_header"},
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
                                "fragment_header": {"fragment_slice_count": 0},
                                "transform_parameters": {
                                    "slice_parameters": {"slices_x": 1, "slices_y": 1},
                                },
                            },
                        },
                        {
                            "parse_info": {
                                "parse_code": "ParseCodes.high_quality_picture_fragment",
                            },
                            "fragment_parse": {
                                "fragment_header": {"fragment_slice_count": 1}
                            },
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
                        {"parse_info": {"parse_code": "ParseCodes.end_of_sequence"}},
                    ],
                },
                f,
            )

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

    @pytest.mark.parametrize(
        "value",
        [
            # Null
            None,
            # Number
            123,
            1.23,
            # Bool
            True,
            False,
            # String (NB: will be executed as python which results in a string)
            "'foobar'",
            # Array
            [],
        ],
    )
    def test_json_root_object_isnt_dict(self, value, tmpdir, capsys):
        spec_filename = str(tmpdir.join("spec.json"))
        bitstream_filename = str(tmpdir.join("out.vc2"))

        with open(spec_filename, "w") as f:
            json.dump(value, f)

        assert main([spec_filename, bitstream_filename]) != 0

        assert capsys.readouterr()[1].startswith(
            "Specification must contain a JSON object"
        )

    def test_missing_end_of_sequence(self, tmpdir, capsys):
        # Note that if the missing end of sequence is not detected the
        # serialiser will be stuck in an infinite loop generating default data
        # units.

        spec_filename = str(tmpdir.join("spec.json"))
        bitstream_filename = str(tmpdir.join("out.vc2"))

        with open(spec_filename, "w") as f:
            json.dump({}, f)

        assert main([spec_filename, bitstream_filename]) != 0

        assert capsys.readouterr()[1].startswith(
            "Specification must end with an 'end of sequence' data unit"
        )

    def test_disallowed_field(self, tmpdir, capsys):
        spec_filename = str(tmpdir.join("spec.json"))
        bitstream_filename = str(tmpdir.join("out.vc2"))

        with open(spec_filename, "w") as f:
            json.dump(
                {
                    "data_units": [
                        {"parse_info": {"parse_code": "ParseCodes.end_of_sequence"}},
                    ],
                    "bad_entry": "'oops'",
                },
                f,
            )

        assert main([spec_filename, bitstream_filename]) != 0

        assert (
            re.match(
                (
                    r"The field u?'bad_entry' is not allowed in dict "
                    r"\(allowed fields: 'data_units', '_state'\)\n"
                ),
                capsys.readouterr()[1],
            )
            is not None
        )

    def test_unused_field(self, tmpdir, capsys):
        spec_filename = str(tmpdir.join("spec.json"))
        bitstream_filename = str(tmpdir.join("out.vc2"))

        with open(spec_filename, "w") as f:
            json.dump(
                {
                    "data_units": [
                        {
                            "parse_info": {"parse_code": "ParseCodes.end_of_sequence"},
                            "picture_parse": {},
                        },
                    ],
                },
                f,
            )

        assert main([spec_filename, bitstream_filename]) != 0

        assert (
            re.match(
                r"Unused field Sequence\['data_units'\]\[0\]\[u?'picture_parse'\]\n",
                capsys.readouterr()[1],
            )
            is not None
        )

    def test_bad_python_eval(self, tmpdir, capsys):
        spec_filename = str(tmpdir.join("spec.json"))
        bitstream_filename = str(tmpdir.join("out.vc2"))

        with open(spec_filename, "w") as f:
            json.dump(
                {"data_units": [{"parse_info": {"parse_code": "ParseCodes.oopsie"}},],},
                f,
            )

        assert main([spec_filename, bitstream_filename]) != 0

        assert (
            re.match(
                r"Error in Python expression: Evaluation of u?'ParseCodes\.oopsie' "
                r"in Sequence\[u?'data_units'\]\[0\]\[u?'parse_info'\]\[u?'parse_code'\] failed: "
                r"AttributeError: oopsie\n",
                capsys.readouterr()[1],
            )
            is not None
        )

    def test_vc2_pseudocode_error(self, tmpdir, capsys):
        spec_filename = str(tmpdir.join("spec.json"))
        bitstream_filename = str(tmpdir.join("out.vc2"))

        # Picture without sequence header will fail to serialise
        with open(spec_filename, "w") as f:
            json.dump(
                {
                    "data_units": [
                        {
                            "parse_info": {
                                "parse_code": "ParseCodes.high_quality_picture",
                            },
                        },
                        {"parse_info": {"parse_code": "ParseCodes.end_of_sequence"}},
                    ],
                },
                f,
            )

        assert main([spec_filename, bitstream_filename]) != 0

        assert capsys.readouterr()[1] == (
            "Unable to construct bitstream at "
            "Sequence['data_units'][0]['picture_parse']['wavelet_transform']['transform_parameters']: "
            "KeyError: 'major_version' "
            "(is a sequence or fragment header missing?)\n"
        )
