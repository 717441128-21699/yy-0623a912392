MATERIAL_PARAMS = {
    "steel_pipe": {
        "φ48×3.0": {
            "outer_diameter": 48.0,
            "thickness": 3.0,
            "inner_diameter": 42.0,
            "area": 4.24,
            "modulus": 2.06e5,
            "f_y": 205.0,
            "f_v": 120.0,
            "weight_per_m": 3.33,
        },
        "φ48×3.5": {
            "outer_diameter": 48.0,
            "thickness": 3.5,
            "inner_diameter": 41.0,
            "area": 4.89,
            "modulus": 2.06e5,
            "f_y": 205.0,
            "f_v": 120.0,
            "weight_per_m": 3.84,
        },
        "φ60×3.5": {
            "outer_diameter": 60.0,
            "thickness": 3.5,
            "inner_diameter": 53.0,
            "area": 6.21,
            "modulus": 2.06e5,
            "f_y": 205.0,
            "f_v": 120.0,
            "weight_per_m": 4.88,
        },
    },
    "wood_joist": {
        "50×80": {
            "width": 50.0,
            "height": 80.0,
            "area": 4000.0,
            "modulus": 9000.0,
            "f_m": 13.0,
            "f_v": 1.4,
            "deflection_limit_ratio": 250,
        },
        "50×100": {
            "width": 50.0,
            "height": 100.0,
            "area": 5000.0,
            "modulus": 9000.0,
            "f_m": 13.0,
            "f_v": 1.4,
            "deflection_limit_ratio": 250,
        },
        "40×80": {
            "width": 40.0,
            "height": 80.0,
            "area": 3200.0,
            "modulus": 9000.0,
            "f_m": 13.0,
            "f_v": 1.4,
            "deflection_limit_ratio": 250,
        },
        "60×90": {
            "width": 60.0,
            "height": 90.0,
            "area": 5400.0,
            "modulus": 9000.0,
            "f_m": 13.0,
            "f_v": 1.4,
            "deflection_limit_ratio": 250,
        },
    },
    "main_beam": {
        "φ48×3.0双钢管": {
            "type": "double_steel",
            "spec": "φ48×3.0",
            "count": 2,
            "area": 8.48,
            "modulus": 2.06e5,
            "f_m": 205.0,
            "f_v": 120.0,
        },
        "φ48×3.5双钢管": {
            "type": "double_steel",
            "spec": "φ48×3.5",
            "count": 2,
            "area": 9.78,
            "modulus": 2.06e5,
            "f_m": 205.0,
            "f_v": 120.0,
        },
        "10#槽钢": {
            "type": "channel",
            "area": 12.74,
            "modulus": 2.06e5,
            "f_m": 215.0,
            "f_v": 125.0,
            "W_x": 39.7,
            "I_x": 198.0,
        },
        "12#槽钢": {
            "type": "channel",
            "area": 15.36,
            "modulus": 2.06e5,
            "f_m": 215.0,
            "f_v": 125.0,
            "W_x": 57.7,
            "I_x": 346.0,
        },
        "14#槽钢": {
            "type": "channel",
            "area": 18.51,
            "modulus": 2.06e5,
            "f_m": 215.0,
            "f_v": 125.0,
            "W_x": 80.5,
            "I_x": 564.0,
        },
        "50×100木方": {
            "type": "wood",
            "width": 50.0,
            "height": 100.0,
            "area": 5000.0,
            "modulus": 9000.0,
            "f_m": 13.0,
            "f_v": 1.4,
        },
    },
    "fastener": {
        "直角扣件": {
            "anti_slip_capacity": 8.0,
        },
        "旋转扣件": {
            "anti_slip_capacity": 8.0,
        },
        "对接扣件": {
            "tensile_capacity": 6.0,
        },
    },
    "concrete": {
        "density": 24.0,
    },
    "template": {
        "plywood_15mm": {
            "thickness": 15.0,
            "weight_per_m2": 0.15 * 6.0,
        },
        "plywood_18mm": {
            "thickness": 18.0,
            "weight_per_m2": 0.18 * 6.0,
        },
    },
    "live_load": {
        "construction_standard": 2.0,
        "construction_heavy": 2.5,
        "pouring_standard": 2.0,
        "pouring_heavy": 4.0,
    },
}


def get_steel_pipe_params(spec):
    if spec in MATERIAL_PARAMS["steel_pipe"]:
        return MATERIAL_PARAMS["steel_pipe"][spec]
    return None


def get_wood_joist_params(spec):
    if spec in MATERIAL_PARAMS["wood_joist"]:
        return MATERIAL_PARAMS["wood_joist"][spec]
    return None


def get_main_beam_params(spec):
    if spec in MATERIAL_PARAMS["main_beam"]:
        return MATERIAL_PARAMS["main_beam"][spec]
    return None


def get_fastener_params(spec):
    if spec in MATERIAL_PARAMS["fastener"]:
        return MATERIAL_PARAMS["fastener"][spec]
    return None


def list_materials(category=None):
    if category:
        if category in MATERIAL_PARAMS:
            return list(MATERIAL_PARAMS[category].keys())
        return []
    return {k: list(v.keys()) for k, v in MATERIAL_PARAMS.items()}
