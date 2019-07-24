import pytest

from sympy import (
    symbols,
    sqrt,
    Matrix,
    MatMul,
    Rational,
    simplify,
    collect,
    expand,
)

from sympy.abc import a, b, c, d, z

from vc2_conformance import tables

from vc2_conformance.wavelet_filter_analysis.quantisation_matrices import (
    StageType,
    fir_filter_noise_gain,
    lifting_stage_to_z_transform,
    wavelet_filter_to_matrix_form,
    convert_between_synthesis_and_analysis,
    analysis_matrix_to_classical_form,
    synthesis_matrix_to_classical_form,
    z_to_coeffs,
    wavelet_filter_to_alpha_beta,
    wavelet_filter_to_synthesis_bit_shift_scale,
    accumulated_noise_gains,
    normalize_noise_gains,
    normalized_noise_gains_to_quantisation_matrix,
    derive_quantisation_matrix,
)


def test_fir_filter_noise_gain():
    assert fir_filter_noise_gain([a, b, c]) == sqrt(a**2 + b**2 + c**2)


@pytest.mark.parametrize("stage,expected", [
    # Check all lifting types
    (
        tables.LiftingStage(
            lift_type=tables.LiftingFilterTypes.even_add_odd,
            S=1,
            L=4,
            D=-1,
            taps=[a, b, c, d],
        ),
        (StageType.update, (a*z**-2 + b*z**-1 + c*z**0 + d*z**1)/2),
    ),
    (
        tables.LiftingStage(
            lift_type=tables.LiftingFilterTypes.even_subtract_odd,
            S=1,
            L=4,
            D=-1,
            taps=[a, b, c, d],
        ),
        (StageType.update, -(a*z**-2 + b*z**-1 + c*z**0 + d*z**1)/2),
    ),
    (
        tables.LiftingStage(
            lift_type=tables.LiftingFilterTypes.odd_add_even,
            S=1,
            L=4,
            D=-1,
            taps=[a, b, c, d],
        ),
        (StageType.predict, (a*z**-1 + b*z**0 + c*z**1 + d*z**2)/2),
    ),
    (
        tables.LiftingStage(
            lift_type=tables.LiftingFilterTypes.odd_subtract_even,
            S=1,
            L=4,
            D=-1,
            taps=[a, b, c, d],
        ),
        (StageType.predict, -(a*z**-1 + b*z**0 + c*z**1 + d*z**2)/2),
    ),
    # Check shift works
    (
        tables.LiftingStage(
            lift_type=tables.LiftingFilterTypes.even_add_odd,
            S=3,
            L=4,
            D=-1,
            taps=[a, b, c, d],
        ),
        (StageType.update, (a*z**-2 + b*z**-1 + c*z**0 + d*z**1)/8),
    ),
    # Check delay works
    (
        tables.LiftingStage(
            lift_type=tables.LiftingFilterTypes.even_add_odd,
            S=1,
            L=4,
            D=1,
            taps=[a, b, c, d],
        ),
        (StageType.update, (a*z**0 + b*z**1 + c*z**2 + d*z**3)/2),
    ),
])
def test_lifting_stage_to_z_transform(stage, expected):
    assert lifting_stage_to_z_transform(stage) == expected


def test_wavelet_filter_to_matrix_form():
    assert wavelet_filter_to_matrix_form(
        tables.LIFTING_FILTERS[tables.WaveletFilters.haar_no_shift]
    ) == MatMul(
        Matrix([
            [1, 0],
            [1, 1],
        ]),
        Matrix([
            [1, -Rational(1, 2)],
            [0, 1],
        ])
    )


def test_convert_between_synthesis_and_analysis():
    # The Daubechies 9 7 wavelet is used here because it uses one of every type
    # of lifting operation.
    synth_params = tables.LIFTING_FILTERS[tables.WaveletFilters.daubechies_9_7]
    analy_params = convert_between_synthesis_and_analysis(synth_params)
    
    synth_matrix = wavelet_filter_to_matrix_form(synth_params)
    analy_matrix = wavelet_filter_to_matrix_form(analy_params)
    
    # If the generated analysis filter matches the synthesis filter, the
    # combined matrices should reduce to an identity.
    assert simplify(MatMul(synth_matrix, analy_matrix).doit()) == Matrix([
        [1, 0],
        [0, 1],
    ])


def test_analysis_matrix_to_classical_form():
    # Check against hand-worked example
    synth_params = tables.LIFTING_FILTERS[tables.WaveletFilters.haar_no_shift]
    analy_params = convert_between_synthesis_and_analysis(synth_params)
    H = wavelet_filter_to_matrix_form(analy_params)
    
    H_0, H_1 = analysis_matrix_to_classical_form(H)
    
    assert collect(expand(H_0), z) == z**1/2 + Rational(1, 2)
    assert collect(expand(H_1), z) == z - 1


def test_synthesis_matrix_to_classical_form():
    # Check against hand-worked example
    synth_params = tables.LIFTING_FILTERS[tables.WaveletFilters.haar_no_shift]
    G = wavelet_filter_to_matrix_form(synth_params)
    
    G_0, G_1 = synthesis_matrix_to_classical_form(G)
    
    assert collect(expand(G_0), z) == z**-1 + 1
    assert collect(expand(G_1), z) == z**-1/2 - Rational(1, 2)


def test_matrix_to_classical_form():
    # Check a more complex case results in filters which cancel out
    synth_params = tables.LIFTING_FILTERS[tables.WaveletFilters.le_gall_5_3]
    analy_params = convert_between_synthesis_and_analysis(synth_params)
    
    G = wavelet_filter_to_matrix_form(synth_params)
    H = wavelet_filter_to_matrix_form(analy_params)
    
    G_0, G_1 = synthesis_matrix_to_classical_form(G)
    H_0, H_1 = analysis_matrix_to_classical_form(H)
    
    assert simplify((G_0 * H_0) + (G_1 * H_1)) == 2


def test_z_to_coeffs():
    # Featuring symbolic coefficients, non-simplified input and some implicit
    # zero terms.
    expr = (a*z**-2 + b*z**-1 + c + d*z**2) * z
    
    assert z_to_coeffs(expr) == {
        -3: d,
        -2: 0,
        -1: c,
        0: b,
        1: a,
    }


def test_wavelet_filter_to_alpha_beta():
    # Hand worked example
    params = tables.LIFTING_FILTERS[tables.WaveletFilters.haar_no_shift]
    
    alpha, beta = wavelet_filter_to_alpha_beta(params)
    assert alpha == sqrt(2)
    assert beta == sqrt(2)/2


@pytest.mark.parametrize("params,exp_scale", [
    (tables.LIFTING_FILTERS[tables.WaveletFilters.haar_no_shift], 1),
    (tables.LIFTING_FILTERS[tables.WaveletFilters.haar_with_shift], Rational(1, 2)),
])
def test_filter_to_synthesis_bit_shift_scale(params, exp_scale):
    assert wavelet_filter_to_synthesis_bit_shift_scale(params) == exp_scale


def test_accumulated_noise_gains():
    alpha_v, beta_v, alpha_h, beta_h, s = symbols(
        r"\alpha_v \beta_v \alpha_h \beta_h s"
    )
    noise_gains = accumulated_noise_gains(alpha_v, beta_v, alpha_h, beta_h, s, 2, 3)
    
    assert noise_gains == {
        0: {"L": s**5 * alpha_h**5 * alpha_v**2},
        1: {"H": s**5 * alpha_h**4 * alpha_v**2 * beta_h},
        2: {"H": s**4 * alpha_h**3 * alpha_v**2 * beta_h},
        3: {"H": s**3 * alpha_h**2 * alpha_v**2 * beta_h},
        4: {
            "HL": s**2 * alpha_h * alpha_v * beta_h * alpha_v,
            "LH": s**2 * alpha_h * alpha_v * alpha_h * beta_v,
            "HH": s**2 * alpha_h * alpha_v * beta_h * beta_v,
        },
        5: {
            "HL": s * beta_h * alpha_v,
            "LH": s * alpha_h * beta_v,
            "HH": s * beta_h * beta_v,
        },
    }


def test_normalize_noise_gains():
    assert normalize_noise_gains({
        0: {"L": 100},
        1: {"H": 200},
        2: {"HL": 300, "LH": 400, "HH": 500},
    }) == {
        0: {"L": 1},
        1: {"H": 2},
        2: {"HL": 3, "LH": 4, "HH": 5},
    }


def test_normalized_noise_gains_to_quantisation_matrix():
    assert normalized_noise_gains_to_quantisation_matrix({
        0: {"L": 1},
        1: {"H": 2},
        2: {"HL": 4, "LH": 5, "HH": 7},
    }) == {
        0: {"L": 0},
        1: {"H": 4},
        2: {"HL": 8, "LH": 9, "HH": 11},
    }


def test_derive_quantisation_matrix():
    # The chosen example is the only asymmetric transform included in the
    # specification. Using this combination ensures that h/v are not swapped
    # around at any point.
    #
    # The values below were taken from the 2017 version of the VC-2
    # specification (SMPTE ST 2042-1:2017) and were computed by an independent
    # author using an independent approach.
    assert derive_quantisation_matrix(
        tables.WaveletFilters.haar_no_shift,
        tables.WaveletFilters.le_gall_5_3,
        3,
        2,
    ) == {
        0: {"L": 2},
        1: {"H": 0},
        2: {"H": 3},
        3: {"HL": 6, "LH": 4, "HH": 2},
        4: {"HL": 6, "LH": 5, "HH": 2},
        5: {"HL": 7, "LH": 5, "HH": 3},
    }
