# -*- coding: utf-8 -*-

import re
import sys
import traceback
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
except Exception:
    tk = None
    filedialog = None
    messagebox = None


HEADING_RE = re.compile(r"^(#{1,6})(?:[ \t]+(.*?)|(.+?))[ \t]*$")


class Section:
    def __init__(self, level, title):
        self.level = level
        self.title = title
        self.content = []
        self.children = []


def parse_heading(line):
    line = line.rstrip("\r\n")

    match = HEADING_RE.match(line)
    if not match:
        return None

    hashes = match.group(1)
    title = match.group(2)

    if title is None:
        title = match.group(3)

    if title is None:
        return None

    title = title.strip()

    if not title:
        return None

    title = re.sub(r"[ \t]+#+[ \t]*$", "", title).strip()

    if not title:
        return None

    return len(hashes), title


def is_fence_start(line):
    stripped = line.strip()

    if stripped.startswith("```"):
        return "```"

    if stripped.startswith("~~~"):
        return "~~~"

    return None


def is_fence_end(line, fence):
    if fence is None:
        return False

    stripped = line.strip()
    return stripped.startswith(fence)


def parse_markdown(text):
    lines = text.splitlines(keepends=True)

    root_content = []
    sections = []
    stack = []

    fence = None

    for line in lines:
        if fence is not None:
            if is_fence_end(line, fence):
                fence = None

            if stack:
                stack[-1].content.append(line)
            else:
                root_content.append(line)

            continue

        new_fence = is_fence_start(line)

        if new_fence is not None:
            fence = new_fence

            if stack:
                stack[-1].content.append(line)
            else:
                root_content.append(line)

            continue

        heading = parse_heading(line)

        if heading is None:
            if stack:
                stack[-1].content.append(line)
            else:
                root_content.append(line)
            continue

        level, title = heading

        section = Section(level, title)

        while stack and stack[-1].level >= level:
            stack.pop()

        if stack:
            stack[-1].children.append(section)
        else:
            sections.append(section)

        stack.append(section)

    return root_content, sections


def append_content(destination, source):
    if not source:
        return

    if not destination:
        destination.extend(source)
        return

    old_has_content = any(line.strip() for line in destination)
    new_has_content = any(line.strip() for line in source)

    if old_has_content and new_has_content:
        if destination[-1].strip() and source[0].strip():
            destination.append("\n")

    destination.extend(source)


def merge_sections(sections):
    result = []
    index = {}

    for section in sections:
        key = (section.level, section.title)

        if key not in index:
            merged = Section(section.level, section.title)
            merged.content = list(section.content)
            merged.children = merge_sections(section.children)

            index[key] = merged
            result.append(merged)
        else:
            existing = index[key]

            append_content(
                existing.content,
                section.content
            )

            existing.children = merge_sections(
                existing.children + section.children
            )

    return result


def render_sections(sections, output):
    for section in sections:
        output.append(
            "#" * section.level
            + " "
            + section.title
            + "\n"
        )

        output.extend(section.content)

        render_sections(
            section.children,
            output
        )


def merge_markdown(text):
    root_content, sections = parse_markdown(text)

    merged_sections = merge_sections(sections)

    output = []
    output.extend(root_content)

    render_sections(
        merged_sections,
        output
    )

    return "".join(output)


def read_text_file(path):
    encodings = (
        "utf-8-sig",
        "utf-8",
        "gb18030",
    )

    last_error = None

    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as error:
            last_error = error

    raise ValueError(
        "无法读取文件。文件既不是有效的 UTF-8，也不是有效的 GB18030。\n"
        + str(last_error)
    )


def make_output_path(input_path):
    base = input_path.with_name(
        input_path.stem + "_合并后" + input_path.suffix
    )

    if not base.exists():
        return base

    number = 2

    while True:
        candidate = input_path.with_name(
            input_path.stem
            + "_合并后_"
            + str(number)
            + input_path.suffix
        )

        if not candidate.exists():
            return candidate

        number += 1


def process_file(filename):
    input_path = Path(filename.strip().strip('"').strip("'"))

    if not input_path.exists():
        raise FileNotFoundError(
            "找不到文件：\n" + str(input_path)
        )

    if not input_path.is_file():
        raise ValueError(
            "指定路径不是文件：\n" + str(input_path)
        )

    text = read_text_file(input_path)

    result = merge_markdown(text)

    output_path = make_output_path(input_path)

    output_path.write_text(
        result,
        encoding="utf-8"
    )

    return output_path


def console_input():
    print("=" * 60)
    print("Markdown 词典章节合并工具")
    print("=" * 60)
    print()
    print("请输入 Markdown 文件路径。")
    print("例如：D:\\词典.md")
    print()

    filename = input("> ").strip()

    if not filename:
        raise ValueError("没有输入文件路径。")

    return process_file(filename)


def gui_input():
    root = tk.Tk()
    root.withdraw()

    try:
        filename = filedialog.askopenfilename(
            title="选择 Markdown 文件",
            filetypes=[
                (
                    "Markdown 文件",
                    "*.md *.markdown *.mdown *.mkd"
                ),
                (
                    "所有文件",
                    "*.*"
                )
            ]
        )

        if not filename:
            return None

        output_path = process_file(filename)

        messagebox.showinfo(
            "处理完成",
            "Markdown 已成功合并。\n\n"
            "输出文件：\n"
            + str(output_path)
        )

        return output_path

    finally:
        root.destroy()


def main():
    try:
        if tk is not None:
            try:
                return gui_input()
            except Exception:
                print()
                print("图形界面运行失败，改用命令行模式。")
                print()

        return console_input()

    except Exception as error:
        print()
        print("=" * 60)
        print("处理失败")
        print("=" * 60)
        print()
        print(str(error))
        print()
        traceback.print_exc()
        print()
        input("按 Enter 键退出...")
        return 1


if __name__ == "__main__":
    sys.exit(main())