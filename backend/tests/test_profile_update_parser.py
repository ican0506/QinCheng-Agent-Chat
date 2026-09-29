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
