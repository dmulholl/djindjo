#!/usr/bin/env python3

import unittest
from djindjo import Template


class TestObject:
    def __init__(self, attribute):
        self.attribute = attribute


data = {
    "object": TestObject("foobar"),
    "number": 123,
    "string": "barfoo",
    "dict": {"foo": "bar"},
    "list": ["foo", "bar", "baz"],
    "true_var": True,
    "false_var": False,
}


class TemplateTests(unittest.TestCase):

    def test_empty_template_string(self):
        template = ""
        rendered = Template(template).render(data)
        self.assertEqual(rendered, "")

    def test_template_with_no_tags(self):
        template = "no tags"
        rendered = Template(template).render(data)
        self.assertEqual(rendered, "no tags")

    def test_comment_tag(self):
        template = "foo{# this is \n a comment #}bar"
        rendered = Template(template).render(data)
        self.assertEqual(rendered, "foobar")

    def test_print_tag_with_number(self):
        template = "{{number}}"
        rendered = Template(template).render(data)
        self.assertEqual(rendered, "123")

    def test_print_tag_with_string(self):
        template = "{{string}}"
        rendered = Template(template).render(data)
        self.assertEqual(rendered, "barfoo")

    def test_print_tag_with_object(self):
        template = "{{object.attribute}}"
        rendered = Template(template).render(data)
        self.assertEqual(rendered, "foobar")

    def test_print_tag_with_dict(self):
        template = "{{dict.foo}}"
        rendered = Template(template).render(data)
        self.assertEqual(rendered, "bar")

    def test_if_tag_with_true_condition(self):
        template = "{% if true_var %}foo{% endif %}"
        rendered = Template(template).render(data)
        self.assertEqual(rendered, "foo")

    def test_if_tag_with_false_condition(self):
        template = "{% if false_var %}foo{% endif %}"
        rendered = Template(template).render(data)
        self.assertEqual(rendered, "")

    def test_if_else_tag_with_true_condition(self):
        template = "{% if true_var %}foo{% else %}bar{% endif %}"
        rendered = Template(template).render(data)
        self.assertEqual(rendered, "foo")

    def test_if_else_tag_with_false_condition(self):
        template = "{% if false_var %}foo{% else %}bar{% endif %}"
        rendered = Template(template).render(data)
        self.assertEqual(rendered, "bar")

    def test_for_tag(self):
        template = "{% for var in list %}{{var}}{% endfor %}"
        rendered = Template(template).render(data)
        self.assertEqual(rendered, "foobarbaz")


if __name__ == "__main__":
    unittest.main()
