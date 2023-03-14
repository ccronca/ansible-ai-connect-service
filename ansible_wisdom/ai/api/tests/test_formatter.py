#!/usr/bin/env python3

from ai.api import formatter as fmtr
from django.test import TestCase


class AnsibleDumperTestCase(TestCase):
    def test_extra_empty_lines(self):
        extra_empty_lines = """---
- name: test empty lines

  copy:
    src: a
    dest: b








"""
        expected = """- name: test empty lines\n  copy:\n    src: a\n    dest: b\n"""
        output = fmtr.normalize_yaml(extra_empty_lines)
        self.assertEqual(output, expected)

    def test_extra_empty_spaces(self):
        """
        extra spaces after values, do not remove them
        """
        extra_empty_spaces = """---
- name: test empty lines

  copy:
    src: a
    dest: b

"""
        expected = """- name: test empty lines\n  copy:\n    src: a\n    dest: b\n"""
        self.assertEqual(fmtr.normalize_yaml(extra_empty_spaces), expected)

    def test_prompt_and_context(self):
        prompt_and_context = """---
- name: test empty lines

  copy:
    src: a
    dest: b



- name: here is the new prompt




"""
        expected = """- name: test empty lines\n  copy:\n    src: a\n    dest: b\n\n- name: here is the new prompt\n"""  # noqa: E501
        self.assertEqual(fmtr.normalize_yaml(prompt_and_context), expected)
        # a, b, _ = fmtr.normalize_yaml(prompt_and_context).rsplit('\n', 2)

    def test_incorrect_indent_name(self):
        """
        extra spaces after values, do not remove them
        """
        incorrect_indent_name = """---

- name: playbook with tasks indented incorrectly

  tasks:
  - name: copy tasks
    copy:
        src: a
        dest: b

"""

        expected = """- name: playbook with tasks indented incorrectly\n  tasks:\n    - name: copy tasks\n      copy:\n        src: a\n        dest: b\n"""  # noqa: E501
        self.assertEqual(fmtr.normalize_yaml(incorrect_indent_name), expected)

    def test_comments(self):
        """
        extra spaces after values, do not remove them
        """
        comments = """---
- name: test empty lines
# I am comment 0
  copy:
    src: a        # I am comment 1
    # I am comment 2
    dest: b

"""
        expected = """- name: test empty lines\n  copy:\n    src: a\n    dest: b\n"""
        self.assertEqual(fmtr.normalize_yaml(comments), expected)

    def test_restore_indentation(self):
        """
        adds necessary extra spaces if original indent > received indent
        """
        original_yaml = "  ansible.builtin.yum:\n    name: '{{ name }}'\n    state: present"
        expected = "      ansible.builtin.yum:\n        name: '{{ name }}'\n        state: present"
        self.assertEqual(fmtr.restore_indentation(original_yaml, 6), expected)

    def test_restore_indentation_two_spaces(self):
        """
        no modifications when original indent == received indent
        """
        original_yaml = "  ansible.builtin.yum:\n    name: '{{ name }}'\n    state: present"
        expected = "  ansible.builtin.yum:\n    name: '{{ name }}'\n    state: present"
        self.assertEqual(fmtr.restore_indentation(original_yaml, 2), expected)

    def test_restore_indentation_zero(self):
        """
        no modifications when original indent < received indent
        """
        original_yaml = "  ansible.builtin.yum:\n    name: '{{ name }}'\n    state: present"
        expected = "  ansible.builtin.yum:\n    name: '{{ name }}'\n    state: present"
        self.assertEqual(fmtr.restore_indentation(original_yaml, 0), expected)


if __name__ == "__main__":
    import yaml

    tests = AnsibleDumperTestCase()
    tests.test_extra_empty_lines()
    tests.test_extra_empty_spaces()
    tests.test_incorrect_indent_name()
    tests.test_comments()
    tests.test_prompt_and_context()
    tests.test_restore_indentation()