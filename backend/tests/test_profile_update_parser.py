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


def test_parse_complete_entrepreneurial_profile_with_exact_graduation_date() -> None:
    patch = ProfileUpdateParser.parse(
        "我在苏州，本科，2025年6月20日毕业，目前创业中，准备创业，连续缴纳社保12个月，公司注册12个月"
    )

    assert patch["city"] == "苏州市"
    assert patch["education"] == "本科"
    assert patch["graduationYear"] == 2025
    assert patch["graduationDate"] == date(2025, 6, 20)
    assert patch["employmentStatus"] == "创业中"
    assert patch["socialInsuranceMonths"] == 12
    assert patch["businessRegistrationMonths"] == 12


def test_parse_iso_graduation_date_and_explicit_year() -> None:
    patch = ProfileUpdateParser.parse("我的毕业日期是2025-06-20，毕业年份是2025")

    assert patch["graduationDate"] == date(2025, 6, 20)
    assert patch["graduationYear"] == 2025


def test_parse_self_reported_unemployment_wording() -> None:
    patch = ProfileUpdateParser.parse(
        "我去年本科毕业，目前待业，我在苏州",
        current_date=date(2026, 9, 30),
    )

    assert patch["city"] == "苏州市"
    assert patch["education"] == "本科"
    assert patch["graduationYear"] == 2025
    assert patch["employmentStatus"] == "待就业"
    assert patch["unemploymentStatus"] == "未就业"


def test_parse_graduation_month_without_inventing_a_day() -> None:
    patch = ProfileUpdateParser.parse("2025年6月毕业")

    assert patch["graduationYear"] == 2025
    assert "graduationDate" not in patch


def test_exact_date_overrides_relative_year_without_losing_date() -> None:
    patch = ProfileUpdateParser.parse(
        "我是去年毕业的，具体是2025年6月20日",
        current_date=date(2026, 9, 30),
    )

    assert patch["graduationYear"] == 2025
    assert patch["graduationDate"] == date(2025, 6, 20)


def test_policy_wording_does_not_mark_user_as_unemployed() -> None:
    assert "employmentStatus" not in ProfileUpdateParser.parse("我想了解待业补贴和待业政策")
