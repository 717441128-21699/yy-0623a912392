#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模板支撑验算工具 - 主入口脚本

使用方法:
  python main.py check examples/single_sample.yaml
  python main.py check examples/batch_sample.yaml -o report.txt
  python main.py list
"""

import sys
from template_checker.cli import main

if __name__ == "__main__":
    sys.exit(main())
