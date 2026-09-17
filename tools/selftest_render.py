#!/usr/bin/env python3
"""Offline self-tests for registry-backed inventory rendering."""

import unittest

from render import RenderError, render_inventory, render_repository_links


def module(name="Name", status="published"):
    return {
        "name": name,
        "repo": "owner/" + name.lower(),
        "status": status,
        "class": {"en": "runtime", "ja": "ランタイム"},
        "owns": {"en": "tasks", "ja": "タスク"},
    }


def registry(*modules):
    return {
        "modules": list(modules),
        "status_labels": {
            "published": {"en": "published", "ja": "公開"},
            "preparing": {"en": "publication in preparation", "ja": "公開準備中"},
        },
    }


class RenderTests(unittest.TestCase):
    def test_published_inventory(self):
        data = registry(module())
        for lang in ("en", "ja"):
            with self.subTest(lang=lang):
                entry = data["modules"][0]
                expected = "| [Name](https://github.com/owner/name) | %s | %s | %s |" % (
                    entry["class"][lang],
                    entry["owns"][lang],
                    data["status_labels"]["published"][lang],
                )
                self.assertEqual(render_inventory(data, lang).splitlines()[2:], [expected])

    def test_preparing_inventory(self):
        data = registry(module(status="preparing"))
        for lang in ("en", "ja"):
            with self.subTest(lang=lang):
                output = render_inventory(data, lang)
                self.assertIn("| **Name** |", output)
                self.assertNotIn("https://github.com/", output)
                self.assertNotIn("](", output)
                self.assertTrue(output.endswith("| %s |" % data["status_labels"]["preparing"][lang]))

    def test_mixed_inventory_preserves_order_and_count(self):
        data = registry(module("Zulu", "preparing"), module("Alpha"), module("Middle", "preparing"))
        rows = render_inventory(data, "en").splitlines()[2:]
        self.assertEqual(
            [row.split(" | ")[0] for row in rows],
            ["| **Zulu**", "| [Alpha](https://github.com/owner/alpha)", "| **Middle**"],
        )

    def test_unsupported_language(self):
        with self.assertRaises(RenderError):
            render_inventory(registry(module()), "unsupported")

    def test_preparing_repository_links_unchanged(self):
        self.assertEqual(
            render_repository_links(registry(module(status="preparing"))),
            "| Module | Link target | State |\n"
            "| --- | --- | --- |\n"
            "| Name | `owner/name` | publication in preparation |",
        )

    def test_name_and_repo_validation_for_both_statuses(self):
        for status in ("published", "preparing"):
            for field in ("name", "repo"):
                for delimiter in ("|", "\n", "\r"):
                    with self.subTest(status=status, field=field, delimiter=delimiter):
                        entry = module(status=status)
                        entry[field] += delimiter
                        with self.assertRaises(RenderError):
                            render_inventory(registry(entry), "en")

    def test_status_flip_adds_link(self):
        entry = module(status="preparing")
        data = registry(entry)
        self.assertIn("| **Name** |", render_inventory(data, "en"))
        entry["status"] = "published"
        output = render_inventory(data, "en")
        self.assertIn("| [Name](https://github.com/owner/name) |", output)
        self.assertNotIn("**Name**", output)


if __name__ == "__main__":
    unittest.main()
