import random
from jinja2 import Environment, FileSystemLoader
from PIL import Image
import imgkit

FOOTER_POOL = {
    "green": [
        "Deficit sustained. Outcome inevitable.",
        "Fat cells filing resignation letters.",
        "Discipline showed up."
    ],
    "amber": [
        "Process over mood.",
        "Stay boring. It works."
    ],
    "red": [
        "Data noted. Adjust tomorrow.",
        "No emotion. Just correction."
    ]
}

def render_dashboard(data):
    env = Environment(loader=FileSystemLoader("render"))
    tpl = env.get_template("dashboard.html")

    status = data["status"]
    footer_text = random.choice(FOOTER_POOL[status])

    html = tpl.render(
        **data,
        footer_text=footer_text,
        footer_color=status
    )

    with open("render/out.html", "w") as f:
        f.write(html)

    imgkit.from_file(
        "render/out.html",
        "render/final.png",
        options={"width":1080, "height":1920}
    )

    return "render/final.png"