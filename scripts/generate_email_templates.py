import os
import re

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

templates_path = os.path.join(PROJECT_ROOT, "templates", "email")
messages_path = os.path.join(PROJECT_ROOT, "templates", "email", "messages")
generated_path = os.path.join(PROJECT_ROOT, "templates", "email", "generated")
languages = ["fi", "sv", "en"]


def get_template_for_message(filename):
    lang = filename.replace(".html", "")[-2:]
    if lang not in languages:
        lang = "fi"
    template_filename = f"base_template_{lang}.html"
    template_path = os.path.join(templates_path, template_filename)
    with open(template_path, "r") as file:
        template = file.read()
    return template


def get_content_tag_line(template):
    return re.search("^.*{{ content }}.*$", template, re.MULTILINE).group(0)


def get_indentation(line):
    return len(line.split("{", 1)[0])


def indent_content(content, indentation):
    content_lines = content.splitlines()
    indented_content = ""
    for line in content_lines:
        if len(line) > 0:
            indented_content = indented_content + indentation * " " + line
        # if line is empty, don't indent
        indented_content = f"{indented_content}\n"
    return indented_content


def generate_template(filename):
    with open(os.path.join(messages_path, filename), "r") as template_file:
        message = template_file.read()

        template = get_template_for_message(filename)
        content_tag_line = get_content_tag_line(template)
        indentation = get_indentation(content_tag_line)
        indented_message_content = indent_content(message, indentation)

        generated_content = template.replace(content_tag_line, indented_message_content)
    return generated_content


def create_generated_folder():
    if not os.path.exists(generated_path):
        os.makedirs(generated_path)


def clear_generated_templates():
    for file_name in os.listdir(generated_path):
        file_path = os.path.join(generated_path, file_name)
        os.remove(file_path)


def save_template(filename, content):
    with open(os.path.join(generated_path, filename), "x") as f:
        f.write(content)


if __name__ == "__main__":
    create_generated_folder()
    clear_generated_templates()
    for message_filename in os.listdir(messages_path):
        generated_template = generate_template(message_filename)
        save_template(message_filename, generated_template)
