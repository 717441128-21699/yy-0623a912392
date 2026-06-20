import sys
import os
import argparse

from .parser import parse_file, ValidationError
from .csv_parser import parse_csv_file
from .calculator import calculate_member
from .output import generate_output, generate_batch_with_errors
from .materials import (
    list_materials,
    list_anti_slip_fasteners,
    load_custom_materials,
    reload_materials,
    validate_materials_data,
    export_default_materials,
    get_materials_source,
)


def _is_csv_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in (".csv", ".tsv", ".txt"):
        return True
    with open(filepath, "r", encoding="utf-8-sig") as f:
        first_line = f.readline()
        if "," in first_line or "\t" in first_line or "|" in first_line or ";" in first_line:
            return True
    return False


def run_check(input_file, output_file=None, verbose=False):
    is_csv = False
    try:
        is_csv = _is_csv_file(input_file)
    except Exception:
        pass

    if is_csv:
        return _run_csv_check(input_file, output_file, verbose)
    else:
        return _run_yaml_check(input_file, output_file, verbose)


def _run_yaml_check(input_file, output_file=None, verbose=False):
    try:
        parsed_data, warnings = parse_file(input_file)
    except ValidationError as e:
        print("[错误] 参数校验失败:")
        errors = str(e).split("; ")
        for err in errors:
            print(f"  - {err}")
        return 1

    if warnings:
        print("[警告] 参数警告:")
        for w in warnings:
            print(f"  - {w}")
        print()

    if parsed_data["模式"] == "single":
        print(f"[信息] 参数解析成功，正在验算...")
        result = calculate_member(parsed_data)
        print(f"  构件: {parsed_data['构件名称']}")

        output = generate_output(parsed_data, result, warnings)

        if output_file:
            generate_output(parsed_data, result, warnings, output_file)
            print(f"  报告已保存至: {output_file}")

        print()
        print(output)

    else:
        print(f"[信息] 参数解析成功，共 {len(parsed_data['构件列表'])} 个构件，正在批量验算...")
        results = []
        for idx, member_params in enumerate(parsed_data["构件列表"], 1):
            print(f"  正在验算 [{idx}/{len(parsed_data['构件列表'])}] "
                  f"{member_params['构件名称']} ... ", end="")
            result = calculate_member(member_params)
            results.append(result)
            status = "通过" if result["全部满足"] else "不通过"
            print(status)

        output = generate_output(parsed_data, results, warnings)

        if output_file:
            generate_output(parsed_data, results, warnings, output_file)
            print(f"\n[信息] 报告已保存至: {output_file}")

        print()
        print(output)

    return 0


def _run_csv_check(input_file, output_file=None, verbose=False):
    try:
        project_info, members, row_errors, warnings = parse_csv_file(input_file)
    except ValidationError as e:
        print(f"[错误] CSV文件解析失败: {e}")
        return 1

    if warnings:
        print("[警告] 参数警告:")
        for w in warnings:
            print(f"  - {w}")
        print()

    if row_errors:
        print(f"[错误] {len(row_errors)} 行参数校验失败（不影响其他构件继续验算）:")
        for err in row_errors:
            print(f"  第{err['行号']}行 [{err.get('构件名', '')}]: {err['错误']}")
        print()

    if not members:
        print("[错误] 没有可验算的构件，所有行均参数错误")
        return 1

    print(f"[信息] CSV解析成功: {len(members)} 个构件可验算, {len(row_errors)} 行跳过")
    print(f"[信息] 材料库来源: {get_materials_source()}")
    print(f"[信息] 正在批量验算...")

    results = []
    for idx, member_params in enumerate(members, 1):
        print(f"  正在验算 [{idx}/{len(members)}] "
              f"{member_params['构件名称']} ... ", end="")
        result = calculate_member(member_params)
        results.append(result)
        status = "通过" if result["全部满足"] else "不通过"
        print(status)

    output = generate_batch_with_errors(project_info, results, warnings, row_errors)

    if output_file:
        from .output import save_report
        save_report(output, output_file)
        print(f"\n[信息] 报告已保存至: {output_file}")

    print()
    print(output)

    if row_errors:
        return 2
    return 0


def list_material_categories(category=None, detail=False):
    from .materials import list_materials as _list_materials, list_anti_slip_fasteners

    CN_TO_EN = {
        "钢管": "steel_pipe",
        "钢": "steel_pipe",
        "木方": "wood_joist",
        "次楞": "wood_joist",
        "木材": "wood_joist",
        "主楞": "main_beam",
        "主梁": "main_beam",
        "主龙骨": "main_beam",
        "扣件": "fastener",
        "混凝土": "concrete",
        "模板": "template",
        "活荷载": "live_load",
    }
    en_category = CN_TO_EN.get(category, category) if category else None

    print(f"[信息] 材料库来源: {get_materials_source()}")

    if en_category == "fastener":
        anti_slip = list_anti_slip_fasteners()
        materials = _list_materials(en_category, detail=detail)
        print(f"\n可用扣件材料:")
        if detail:
            for name, spec in materials.items():
                anti = "(可抗滑)" if name in anti_slip else "(仅对接/抗拉)"
                remark = spec.get("remark", "")
                print(f"  - {name} {anti} {remark}")
        else:
            for item in materials:
                anti = " (可用于抗滑)" if item in anti_slip else " (不适用抗滑)"
                print(f"  - {item}{anti}")
        print()
        return

    materials = _list_materials(en_category, detail=detail)
    if category:
        print(f"\n可用{category}材料:")
        if detail:
            for name, spec in materials.items():
                remark = spec.get("remark", "")
                spec_str = ", ".join(f"{k}={v}" for k, v in spec.items()
                                     if k not in ("remark",) and not k.startswith("_"))
                print(f"  - {name}: {spec_str} {remark}")
        else:
            for item in materials:
                print(f"  - {item}")
    else:
        print("\n可用材料规格:")
        for cat, items in materials.items():
            cn_name = {
                "steel_pipe": "钢管",
                "wood_joist": "木方(次楞)",
                "main_beam": "主楞",
                "fastener": "扣件",
                "concrete": "混凝土",
                "template": "模板",
                "live_load": "施工活荷载",
            }.get(cat, cat)
            print(f"\n  {cn_name} ({cat}):")
            for item in items:
                print(f"    - {item}")
    print()


def handle_materials_command(args):
    if args.subcommand == "list":
        list_material_categories(args.category, detail=args.detail)
        return 0

    elif args.subcommand == "load":
        if not os.path.exists(args.file):
            print(f"[错误] 文件不存在: {args.file}")
            return 1
        success, msg = load_custom_materials(args.file)
        if success:
            print(f"[成功] {msg}")
        else:
            print(f"[错误] {msg}")
        return 0 if success else 1

    elif args.subcommand == "reload":
        source = reload_materials()
        print(f"[成功] 已重新加载材料库: {source}")
        return 0

    elif args.subcommand == "validate":
        if not os.path.exists(args.file):
            print(f"[错误] 文件不存在: {args.file}")
            return 1
        import json
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "_meta" in data:
                data.pop("_meta")
        except Exception as e:
            print(f"[错误] 无法读取JSON文件: {e}")
            return 1

        errors = validate_materials_data(data)
        if errors:
            print(f"[错误] 材料库校验失败，共 {len(errors)} 个问题:")
            for err in errors:
                print(f"  - {err}")
            return 1
        else:
            print(f"[成功] 材料库校验通过，可正常使用")
            return 0

    elif args.subcommand == "export":
        out_path = args.output or "materials_template.json"
        result = export_default_materials(out_path)
        print(f"[成功] 已导出默认材料库模板至: {result}")
        print("       可在此基础上修改自定义规格，然后用 materials load 加载")
        return 0

    elif args.subcommand == "source":
        print(f"[信息] 当前材料库来源: {get_materials_source()}")
        return 0

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="模板支撑验算命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  验算单个构件(YAML):
    python main.py check examples/single_sample.yaml

  批量验算(YAML):
    python main.py check examples/batch_sample.yaml

  批量验算(CSV/表格):
    python main.py check examples/batch_sample.csv
    python main.py check examples/batch_with_errors.csv -o report.txt

  材料库管理:
    python main.py materials list
    python main.py materials list -c fastener --detail
    python main.py materials export -o my_materials.json
    python main.py materials validate my_materials.json
    python main.py materials load my_materials.json
    python main.py materials source
    python main.py materials reload
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    check_parser = subparsers.add_parser("check", help="验算模板支撑(支持YAML/CSV)")
    check_parser.add_argument("input", help="参数文件路径 (YAML 或 CSV/表格格式)")
    check_parser.add_argument("-o", "--output", help="输出报告文件路径")
    check_parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息")

    materials_parser = subparsers.add_parser("materials", help="材料库管理")
    materials_sub = materials_parser.add_subparsers(dest="subcommand", help="材料库子命令")

    list_parser = materials_sub.add_parser("list", help="列出可用材料")
    list_parser.add_argument("-c", "--category", help="指定材料类别")
    list_parser.add_argument("-d", "--detail", action="store_true", help="显示详细参数")

    load_parser = materials_sub.add_parser("load", help="加载自定义材料库(JSON)")
    load_parser.add_argument("file", help="材料库JSON文件路径")

    materials_sub.add_parser("reload", help="重新加载默认材料库")
    materials_sub.add_parser("source", help="显示当前材料库来源")

    validate_parser = materials_sub.add_parser("validate", help="校验材料库文件格式")
    validate_parser.add_argument("file", help="材料库JSON文件路径")

    export_parser = materials_sub.add_parser("export", help="导出默认材料库模板")
    export_parser.add_argument("-o", "--output", help="输出文件路径")

    args = parser.parse_args()

    if args.command == "check":
        if not os.path.exists(args.input):
            print(f"[错误] 文件不存在: {args.input}")
            return 1
        return run_check(args.input, args.output, args.verbose)

    elif args.command == "materials":
        if not args.subcommand:
            materials_parser.print_help()
            return 1
        return handle_materials_command(args)

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
