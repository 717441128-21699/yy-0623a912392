import math

CONCRETE_DENSITY = 24.0
GAMMA_G = 1.35
GAMMA_Q = 1.4
GAMMA_Q_VIBRATION = 1.4


class CalculationResult:
    def __init__(self, item_name):
        self.item_name = item_name
        self.passed = False
        self.calculated_value = 0.0
        self.limit_value = 0.0
        self.ratio = 0.0
        self.suggestions = []
        self.details = {}

    def to_dict(self):
        return {
            "项目": self.item_name,
            "是否满足": "满足" if self.passed else "不满足",
            "计算值": self.calculated_value,
            "限值": self.limit_value,
            "比值": round(self.ratio, 3),
            "建议": self.suggestions,
            "详细": self.details,
        }


def calculate_loads(params):
    member_type = params["构件类型"]
    loads = {}

    if member_type == "楼板":
        slab_thickness_m = params["混凝土厚度"] / 1000.0
        concrete_load = CONCRETE_DENSITY * slab_thickness_m
        template_load = params.get("模板自重", 0.3)
        dead_load = concrete_load + template_load

        live_load = params.get("施工活荷载", 2.5)
        vibration_load = params.get("振捣荷载", 2.0)

        loads["恒载标准值"] = dead_load
        loads["活载标准值"] = live_load
        loads["振捣荷载标准值"] = vibration_load
        loads["基本组合设计值"] = (
            GAMMA_G * dead_load
            + GAMMA_Q * max(live_load, vibration_load)
        )
        loads["作用面积"] = params["立杆纵距"] * params["立杆横距"]

    elif member_type == "梁":
        beam_width_m = params["梁宽"] / 1000.0
        beam_height_m = params["梁高"] / 1000.0
        concrete_load = CONCRETE_DENSITY * beam_width_m * beam_height_m

        template_load_per_m2 = params.get("模板自重", 0.3)
        template_load = template_load_per_m2 * beam_width_m

        dead_load = concrete_load + template_load

        live_load_per_m2 = params.get("施工活荷载", 2.5)
        live_load = live_load_per_m2 * beam_width_m

        vibration_load_per_m2 = params.get("振捣荷载", 2.0)
        vibration_load = vibration_load_per_m2 * beam_width_m

        loads["恒载标准值"] = dead_load
        loads["活载标准值"] = live_load
        loads["振捣荷载标准值"] = vibration_load
        loads["基本组合设计值"] = (
            GAMMA_G * dead_load
            + GAMMA_Q * max(live_load, vibration_load)
        )
        loads["作用间距"] = params["立杆纵距"]

    return loads


def check_pole_capacity(params):
    result = CalculationResult("立杆承载力")

    steel = params["立杆钢管"]
    bracket = params
    member_type = params["构件类型"]

    loads = calculate_loads(params)

    if member_type == "楼板":
        N = loads["基本组合设计值"] * loads["作用面积"]
    else:
        N = loads["基本组合设计值"] * loads["作用间距"]

    step = bracket["步距"]
    mu = 1.5
    l0 = mu * step
    i = steel["outer_diameter"] / 4.0
    lambda_ = l0 * 1000 / i

    f_y = steel["f_y"]
    if lambda_ <= 91.4:
        phi = 1.0 - 0.65 * (lambda_ / 91.4) ** 2
    else:
        phi = 3450 / (lambda_ ** 2)

    A = steel["area"] * 100
    sigma = N * 1000 / (phi * A)
    f_design = f_y

    result.calculated_value = round(sigma, 1)
    result.limit_value = f_design
    result.ratio = sigma / f_design
    result.passed = sigma <= f_design

    result.details = {
        "轴力设计值(N)": f"{round(N, 2)} kN",
        "步距(h)": f"{round(step, 2)} m",
        "计算长度系数(μ)": mu,
        "计算长度(l0)": f"{round(l0, 2)} m",
        "回转半径(i)": f"{round(i, 2)} mm",
        "长细比(λ)": round(lambda_, 1),
        "稳定系数(φ)": round(phi, 4),
        "钢管截面积(A)": f"{round(A, 2)} mm2",
        "压应力(σ)": f"{round(sigma, 1)} N/mm2",
        "钢材强度设计值(f)": f"{f_design} N/mm2",
    }

    if not result.passed:
        ratio = result.ratio
        if ratio > 1.3:
            result.suggestions.append("增加立杆数量或减小立杆纵距、横距")
        if ratio > 1.1:
            result.suggestions.append("减小步距以提高稳定系数")
        if ratio > 1.0:
            result.suggestions.append("换用壁厚更大的钢管规格")
    else:
        result.suggestions.append("立杆布置合理，承载力满足要求")

    return result


def check_joist_deflection(params):
    result = CalculationResult("次楞挠度")

    wood = params["次楞木方"]
    joist_spacing = params["次楞间距"] / 1000.0
    main_beam_spacing = params["主楞间距"]

    loads = calculate_loads(params)

    if params["构件类型"] == "楼板":
        q_standard = loads["恒载标准值"] * joist_spacing
    else:
        beam_width = params["梁宽"] / 1000.0
        q_standard = loads["恒载标准值"] / beam_width * joist_spacing

    L_mm = main_beam_spacing * 1000
    b = wood["width"]
    h = wood["height"]
    E = wood["modulus"]

    I = b * h ** 3 / 12.0

    q_n_per_mm = q_standard

    deflection = 5 * q_n_per_mm * L_mm ** 4 / (384 * E * I)

    limit_ratio = wood.get("deflection_limit_ratio", 250)
    deflection_limit = L_mm / limit_ratio

    result.calculated_value = round(deflection, 2)
    result.limit_value = round(deflection_limit, 2)
    result.ratio = deflection / deflection_limit
    result.passed = deflection <= deflection_limit

    result.details = {
        "计算跨度(L)": f"{round(main_beam_spacing, 3)} m",
        "均布线荷载标准值(qk)": f"{round(q_standard, 3)} kN/m",
        "木方截面(b×h)": f"{b}×{h} mm",
        "惯性矩(I)": f"{round(I, 2)} mm4",
        "弹性模量(E)": f"{E} N/mm2",
        "计算挠度(ν)": f"{round(deflection, 2)} mm",
        "挠度限值([ν])": f"{round(deflection_limit, 2)} mm (L/{limit_ratio})",
    }

    if not result.passed:
        ratio = result.ratio
        if ratio > 1.3:
            result.suggestions.append("减小次楞间距或减小主楞跨度")
        if ratio > 1.1:
            result.suggestions.append("换用更大截面的木方")
        if ratio > 1.0:
            result.suggestions.append("增加主楞支承点以减小跨度")
    else:
        result.suggestions.append("次楞挠度满足要求")

    return result


def check_main_beam_strength(params):
    result = CalculationResult("主楞强度")

    main_beam = params["主楞"]
    bracket = params

    loads = calculate_loads(params)

    if params["构件类型"] == "楼板":
        span_count = 1
        joist_spacing = bracket["主楞间距"]
        load_per_length = loads["基本组合设计值"] * joist_spacing
    else:
        span_count = 1
        load_per_length = loads["基本组合设计值"]

    L = bracket["立杆横距"]
    L_mm = L * 1000

    if main_beam["type"] == "double_steel":
        from .materials import get_steel_pipe_params
        steel = get_steel_pipe_params(main_beam["spec"])
        D = steel["outer_diameter"]
        d = steel["inner_diameter"]
        W_x = math.pi * (D ** 4 - d ** 4) / (32 * D) * main_beam["count"]
        I_x = math.pi * (D ** 4 - d ** 4) / 64 * main_beam["count"]
        f_m = main_beam["f_m"]
        f_v = main_beam["f_v"]
        A = main_beam["area"] * 100

    elif main_beam["type"] == "channel":
        W_x = main_beam["W_x"] * 1000
        I_x = main_beam["I_x"] * 10000
        f_m = main_beam["f_m"]
        f_v = main_beam["f_v"]
        A = main_beam["area"] * 100

    elif main_beam["type"] == "wood":
        b = main_beam["width"]
        h = main_beam["height"]
        W_x = b * h ** 2 / 6.0
        I_x = b * h ** 3 / 12.0
        f_m = main_beam["f_m"]
        f_v = main_beam["f_v"]
        A = main_beam["area"]

    q_n_per_mm = load_per_length
    M = q_n_per_mm * L_mm ** 2 / 8.0
    sigma_m = M / W_x

    V = q_n_per_mm * L_mm / 2.0
    tau = 1.5 * V / A

    strength_passed = sigma_m <= f_m
    shear_passed = tau <= f_v

    result.calculated_value = round(sigma_m, 1)
    result.limit_value = f_m
    result.ratio = sigma_m / f_m
    result.passed = strength_passed and shear_passed

    result.details = {
        "计算跨度(L)": f"{round(L, 3)} m",
        "线荷载设计值(q)": f"{round(load_per_length, 2)} kN/m",
        "最大弯矩(M)": f"{round(M, 1)} N-mm",
        "抗弯截面模量(Wx)": f"{round(W_x, 2)} mm3",
        "弯曲正应力(σ)": f"{round(sigma_m, 1)} N/mm2",
        "抗弯强度设计值(f)": f"{f_m} N/mm2",
        "最大剪力(V)": f"{round(V, 1)} N",
        "剪应力(τ)": f"{round(tau, 2)} N/mm2",
        "抗剪强度设计值(fv)": f"{f_v} N/mm2",
    }

    if not result.passed:
        ratio = result.ratio
        if not strength_passed:
            if ratio > 1.3:
                result.suggestions.append("减小立杆横距或减小主楞跨度")
            if ratio > 1.1:
                result.suggestions.append("调整主楞规格，采用更大截面")
            if ratio > 1.0:
                result.suggestions.append("增加立杆以减小主楞计算跨度")
        if not shear_passed:
            result.suggestions.append("主楞抗剪不满足，建议增大截面")
    else:
        result.suggestions.append("主楞强度满足要求")

    return result


def check_fastener_slip(params):
    result = CalculationResult("扣件抗滑")

    fastener = params["扣件"]
    fastener_capacity = fastener["anti_slip_capacity"]

    loads = calculate_loads(params)

    if params["构件类型"] == "楼板":
        N = loads["基本组合设计值"] * loads["作用面积"]
    else:
        N = loads["基本组合设计值"] * loads["作用间距"]

    fastener_count = 1
    slip_resistance = fastener_capacity * fastener_count

    result.calculated_value = round(N, 2)
    result.limit_value = slip_resistance
    result.ratio = N / slip_resistance
    result.passed = N <= slip_resistance

    result.details = {
        "立杆轴力设计值(N)": f"{round(N, 2)} kN",
        "单扣件抗滑承载力设计值": f"{fastener_capacity} kN",
        "扣件数量": fastener_count,
        "总抗滑承载力": f"{slip_resistance} kN",
    }

    if not result.passed:
        ratio = result.ratio
        if ratio > 1.5:
            result.suggestions.append("大幅减小立杆间距或增加立杆")
        if ratio > 1.2:
            result.suggestions.append("采用双扣件抗滑")
        if ratio > 1.0:
            result.suggestions.append("减小立杆纵距或横距")
    else:
        result.suggestions.append("扣件抗滑满足要求")

    return result


def run_checks(params, items=None):
    if items is None:
        items = params.get("验算项目", [
            "立杆承载力",
            "扣件抗滑",
            "次楞挠度",
            "主楞强度",
        ])

    results = {}

    if "立杆承载力" in items:
        results["立杆承载力"] = check_pole_capacity(params)

    if "扣件抗滑" in items:
        results["扣件抗滑"] = check_fastener_slip(params)

    if "次楞挠度" in items:
        results["次楞挠度"] = check_joist_deflection(params)

    if "主楞强度" in items:
        results["主楞强度"] = check_main_beam_strength(params)

    return results


def calculate_member(params):
    results = run_checks(params)

    all_passed = all(r.passed for r in results.values())

    return {
        "构件名称": params.get("构件名称", ""),
        "构件类型": params.get("构件类型", ""),
        "全部满足": all_passed,
        "各项结果": results,
        "参数": params,
    }
