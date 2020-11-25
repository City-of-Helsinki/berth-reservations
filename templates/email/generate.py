import os
import re


messages_path = os.path.join(os.getcwd(), 'messages')
generated_path = os.path.join(os.getcwd(), 'generated')
template_file_extension = '.html'


def get_template_for_message(filename):
    lang = filename.replace(template_file_extension, '')[-2:]
    if lang != 'fi' and lang != 'sv' and lang != 'en':
        lang = 'fi'
    template_filename = 'base_template_' + lang + template_file_extension
    template_path = os.path.join(os.getcwd(), template_filename)
    return open(template_path, 'r').read()


def get_content_tag_line(template):
    return re.search('^.*{{ content }}.*$', template, re.MULTILINE).group(0)


def get_indentation(line):
    return len(line.split('{', 1)[0])


def indent_content(content, indentation):
    content_lines = content.splitlines()
    indented_content = ''
    for line in content_lines:
        if len(line) > 0:
            indented_content = indented_content + indentation * ' ' + line + '\n'
        # if line is empty, don't indent
        else:
            indented_content = indented_content + '\n'
    return indented_content


def generate_template(filename):
    message = open(os.path.join(messages_path, filename), 'r').read()

    template = get_template_for_message(filename)
    content_tag_line = get_content_tag_line(template)
    indentation = get_indentation(content_tag_line)
    indented_message_content = indent_content(message, indentation)

    generated_content = template.replace(content_tag_line, indented_message_content)
    return generated_content


def clear_generated_templates():
    file_list = [f for f in os.listdir(generated_path) if f.endswith(template_file_extension)]
    for f in file_list:
        os.remove(os.path.join(generated_path, f))


def save_template(filename, content):
    with open(os.path.join(generated_path, filename), 'x') as f:
        f.write(content)


if __name__ == "__main__":
    clear_generated_templates()
    for message_filename in os.listdir(messages_path):
        generated_template = generate_template(message_filename)
        save_template(message_filename, generated_template)