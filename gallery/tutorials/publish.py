
# ./publish.py
#
# Publish tutorials from analitico-sdk to analitico-site
# where they can be built into the static pages that are
# then served with analitico's website gallery.

from pathlib import Path
import shutil
import yaml
import re

src_tutorials = Path(__file__).parent

# analitico-site repo should be checked out next to analitico-sdk
dst_tutorials = (src_tutorials / "../../../analitico-site/docs/_tutorials/").resolve()
dst_avatars = (src_tutorials / "../../../analitico-site/docs/assets/avatars").resolve()
assert dst_tutorials.is_dir()
assert dst_avatars.is_dir()

# scan tutorials and find the ones that have a markdown file describing them and can be published
for src_markdown in src_tutorials.glob("*/*/*.markdown"):
    src_parent = src_markdown.parent
    item_id = src_parent.parts[-1]
    item_type = src_parent.parts[-2][:-1]
    print(f"\n{src_parent.parts[-2]}/{src_parent.parts[-1]}")

    # parse and validate yaml header in markdown file
    with open(src_markdown, "r") as f:
        item_markdown = f.read()

        # yaml header is --- dadada ---
        idx_0 = item_markdown.find("---\n")
        idx_1 = item_markdown.find("---\n", idx_0+1)
        item_yaml = yaml.load(item_markdown[idx_0 + 4: idx_1], Loader=yaml.Loader)
        item_yaml["id"] = item_id
        item_yaml["type"] = item_type

        # title and description are mandatory
        assert "title" in item_yaml, "title is missing"
        assert "description" in item_yaml, "description is missing"

        # copy avatar image (if present)
        src_avatar = src_parent / "avatar.jpg"
        if src_avatar.is_file():
            dst_avatar = dst_avatars / (item_id + ".jpg")
            shutil.copy(src_avatar, dst_avatar)
            item_yaml["image"] = f"/assets/avatars/{item_id}.jpg"
            print(f"{src_avatar} -> {dst_avatar}")

    # copy markdown with tutorial description
    dst_markdown = dst_tutorials / (item_id + ".markdown")
    with open(dst_markdown, "w+") as f:
        item_yaml = yaml.dump(item_yaml)
        item_markdown = f"---\n{item_yaml}\n---\n{item_markdown[idx_1+4:]}"
        f.write(item_markdown)
