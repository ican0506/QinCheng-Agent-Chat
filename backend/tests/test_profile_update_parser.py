from datetime import date

from app.services.profile_update_parser import ProfileUpdateParser


def test_parse_browser_turn_two_profile_patch_without_inventing_a_day() -> None:
    patch = ProfileUpdateParser.parse("我在苏州，本科，2025年6月毕业，目前未就业")

    assert patch["city"] == "苏州市"
    assert patch["education"] == "本科"
    assert patch["graduationYear"] == 2025
    # 用户只提供到年月；date 字段不能用虚构的某一天表示。
    assert "graduationDate" not in patch
    assert patch["employmentStatus"] == "待就业"
    assert patch["unemploymentStatus"] == "未就业"


def test_parse_explicit_non_entrepreneurial_job_seeking_intent() -> None:
    patch = ProfileUpdateParser.parse("我不创业，只打算找工作")

    assert patch["entrepreneurshipIntent"] is False
    assert patch["jobSeekingIntent"] is True


def test_parse_browser_wording_for_explicit_non_entrepreneurial_job_seeking_intent() -> None:
    patch = ProfileUpdateParser.parse("我不是要创业，我就是想找个工作")

    assert patch["entrepreneurshipIntent"] is False
    assert patch["jobSeekingIntent"] is True


def test_parse_relative_graduation_year_without_inventing_a_date() -> None:
    patch = ProfileUpdateParser.parse(
        "我去年本科毕业，现在还没找到工作，我在苏州",
        current_date=date(2026, 9, 30),
    )

    assert patch["graduationYear"] == 2025
    assert "graduationDate" not in patch
    assert patch["employmentStatus"] == "待就业"
    assert patch["unemploymentStatus"] == "未就业"


def test_parse_all_supported_relative_graduation_years() -> None:
    current_date = date(2026, 9, 30)

    assert ProfileUpdateParser.parse("我今年毕业", current_date=current_date)["graduationYear"] == 2026
    assert ProfileUpdateParser.parse("我去年毕业", current_date=current_date)["graduationYear"] == 2025
    assert ProfileUpdateParser.parse("我前年毕业", current_date=current_date)["graduationYear"] == 2024
    assert ProfileUpdateParser.parse("我明年毕业", current_date=current_date)["graduationYear"] == 2027
