import sys
import os
import argparse

from .parser import parse_file, ValidationError
from .calculator import calculate_member
from .output import generate_output
from .materials import list_materials


def run_check(input_file, output_file=None, verbose=False):
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


def list_material_categories(category=None):
    materials = list_materials(category)
    if category:
        print(f"\n可用{category}材料:")
        for item in materials:
            print(f"  - {item}")
    else:
        print("\n可用材料规格:")
        for cat, items in materials.items():
            print(f"\n  {cat}:")
            for item in items:
                print(f"    - {item}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="模板支撑验算工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  验算单个构件:
  python -m template_checker check examples/single_sample.yaml

  批量验算并输出到文件:
  python -m template_checker check examples/batch_sample.yaml -o report.txt

  列出可用材料:
  python -m template_checker list
  python -m template_checker list --category steel_pipe
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    check_parser = subparsers.add_parser("check", help="验算模板支撑")
    check_parser.add_argument("input", help="参数文件路径 (YAML格式)")
    check_parser.add_argument("-o", "--output", help="输出报告文件路径")
    check_parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息")

    list_parser = subparsers.add_parser("list", help="列出可用材料规格")
    list_parser.add_argument(
        "-c", "--category",
        help="指定材料类别 (如 steel_pipe, wood_joist, main_beam, fastener"
    )

    args = parser.parse_args()

    if args.command == "check":
        if not os.path.exists(args.input):
            print(f"✗ 文件不存在: {args.input}")
            return 1

        return run_check(args.input, args.output, args.verbose)

    elif args.command == "list":
        list_material_categories(args.category)
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
