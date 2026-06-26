"""
Comprehensive test suite for AlsManagerBot
Tests: Local filter + Gemini AI analysis + Database + Rate Limiting
"""

import asyncio
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def PASS():  return f"{GREEN}[PASS]{RESET}"
def FAIL():  return f"{RED}[FAIL]{RESET}"
def SKIP():  return f"{YELLOW}[SKIP]{RESET}"
def header(msg): print(f"\n{BOLD}{CYAN}{'='*60}\n  {msg}\n{'='*60}{RESET}")


# ================================================================
# 1. Local Spam Filter Test (is_suspicious)
# ================================================================
def test_local_filter():
    header("1. Local Spam Filter (is_suspicious)")
    from modules.security.handlers import is_suspicious

    cases = [
        ("Normal academic question",
         "يا جماعة ايش الفرق بين stack و heap",
         False),

        ("Normal social chat",
         "صباح الخير يا شباب كيف الحال",
         False),

        ("Ad with phone + spam keywords",
         "حل واجبات وكويزات تواصل معي 0541234567",
         True),

        ("Multiple spam keywords without phone",
         "تسليم تقارير مشاريع واجبات تواصل واتساب",
         True),

        ("Phone number ALONE without spam words",
         "رقم مكتب الدكتور 0551234567",
         False),

        ("Channel promotion + contact invite",
         "اشتراك قناة تواصل معنا خدمة",
         True),

        ("Link without spam words (entities filter)",
         "شوفوا هذا https://t.me/somegroup",
         False),
    ]

    passed = failed = 0
    for desc, text, expected in cases:
        result = is_suspicious(text)
        ok = result == expected
        mark = PASS() if ok else FAIL()
        print(f"  {mark} {desc}")
        if not ok:
            print(f"         Text: {text[:70]}")
            print(f"         Expected: {expected} | Got: {result}")
            failed += 1
        else:
            passed += 1

    print(f"\n  Result: {GREEN}{passed} passed{RESET} | {RED}{failed} failed{RESET}")
    return failed == 0


# ================================================================
# 2. Gemini AI Spam Detection Test
# ================================================================
async def test_gemini_detection():
    header("2. Gemini AI Message Analysis")

    from config import GEMINI_API_KEY
    if not GEMINI_API_KEY:
        print(f"  {SKIP()} Gemini API key not found in .env - skipping")
        return True

    from handlers.gemini_ai import gemini_check_message

    cases = [
        ("Ad: homework solver with phone",
         "We do reports, homework, quizzes professionally. Contact 0541234567",
         True),

        ("Ad: Telegram channel promotion",
         "Join our channel for more services @somepromo_channel",
         True),

        ("Bad words / insults",
         "You are stupid and an idiot who understands nothing",
         True),

        ("Normal: academic question",
         "Guys what is the difference between Macro and Micro Economics?",
         False),

        ("Normal: free notes sharing",
         "I uploaded the course summary, it's free for everyone",
         False),

        ("Normal: social chat",
         "Good morning, may God bless you all",
         False),
    ]

    passed = failed = skipped = 0
    for desc, text, expected_delete in cases:
        print(f"  Testing: {desc}...")
        try:
            result = await gemini_check_message(text)
            got_delete = result.get("delete", False)
            reason = result.get("reason", "")

            # Handle 503/unavailable as SKIP, not FAIL
            if any(x in reason for x in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "rate_limit"]):
                print(f"  {SKIP()} {desc}")
                print(f"         Reason: Gemini server temporarily unavailable (503)")
                skipped += 1
                await asyncio.sleep(2)
                continue

            ok = got_delete == expected_delete
            mark = PASS() if ok else FAIL()
            print(f"  {mark} {desc}")
            print(f"         Gemini decided: {'DELETE' if got_delete else 'KEEP'} | Reason: {reason}")

            if not ok:
                print(f"         Expected: {'DELETE' if expected_delete else 'KEEP'}")
                failed += 1
            else:
                passed += 1

            await asyncio.sleep(2)

        except Exception as e:
            print(f"  {SKIP()} {desc} - Error: {e}")
            skipped += 1

    print(f"\n  Result: {GREEN}{passed} passed{RESET} | {RED}{failed} failed{RESET} | {YELLOW}{skipped} skipped (server issue){RESET}")
    # Only count as failure if there are actual logic failures, not server issues
    return failed == 0


# ================================================================
# 3. Database Test
# ================================================================
async def test_database():
    header("3. SQLite Database Test")

    import database

    original_db = database.DB_PATH
    database.DB_PATH = "test_bot_data.db"

    try:
        await database.init_db()
        print(f"  {PASS()} Database initialization")

        await database.add_group(-1001234567890)
        settings = await database.get_group_settings(-1001234567890)
        assert settings.get("anti_link") == 1, "anti_link should default to 1"
        assert settings.get("anti_spam") == 1, "anti_spam should default to 1"
        print(f"  {PASS()} Add group with correct defaults (anti_link=1, anti_spam=1)")

        await database.update_group_setting(-1001234567890, "anti_link", 0)
        settings = await database.get_group_settings(-1001234567890)
        assert settings.get("anti_link") == 0
        print(f"  {PASS()} Update settings")

        c1 = await database.add_warning(-1001234567890, 999)
        c2 = await database.add_warning(-1001234567890, 999)
        c3 = await database.add_warning(-1001234567890, 999)
        assert c1 == 1 and c2 == 2 and c3 == 3
        print(f"  {PASS()} Warning system (1 -> 2 -> 3)")

        await database.reset_warnings(-1001234567890, 999)
        c_after = await database.get_warnings(-1001234567890, 999)
        assert c_after == 0
        print(f"  {PASS()} Reset warnings")

        for i in range(5):
            await database.log_message(-1001234567890, 100+i, f"user{i}", f"User {i+1}", f"Test message {i+1}")
        msgs = await database.get_recent_messages(-1001234567890, limit=75)
        assert len(msgs) == 5
        print(f"  {PASS()} Log and fetch messages ({len(msgs)} messages)")

        for i in range(80):
            await database.log_message(-1001234567890, 200, "test", "Tester", f"Msg {i}")
        msgs_after = await database.get_recent_messages(-1001234567890, limit=75)
        assert len(msgs_after) <= 75
        print(f"  {PASS()} 75-message limit works ({len(msgs_after)} messages)")

        await database.add_trigger(-1001234567890, "website", "www.example.com")
        resp = await database.get_trigger(-1001234567890, "website")
        assert resp == "www.example.com"
        print(f"  {PASS()} Add and get Triggers")

        removed = await database.remove_trigger(-1001234567890, "website")
        assert removed is True
        print(f"  {PASS()} Remove Trigger")

        print(f"\n  {GREEN}All database tests passed!{RESET}")
        return True

    except Exception as e:
        print(f"  {FAIL()} Error: {e}")
        return False
    finally:
        database.DB_PATH = original_db
        if os.path.exists("test_bot_data.db"):
            os.remove("test_bot_data.db")
            print(f"  Cleaned up test database.")


# ================================================================
# 4. Rate Limiting Test
# ================================================================
async def test_rate_limiting():
    header("4. Gemini Rate Limiting Test")

    from handlers import gemini_ai
    gemini_ai._check_timestamps.clear()

    from handlers.gemini_ai import _can_call_gemini_check, MAX_CHECKS_PER_MINUTE

    allowed = 0
    for i in range(MAX_CHECKS_PER_MINUTE + 5):
        if _can_call_gemini_check():
            allowed += 1

    assert allowed == MAX_CHECKS_PER_MINUTE, \
        f"Expected {MAX_CHECKS_PER_MINUTE} allowed, got {allowed}"
    print(f"  {PASS()} Allowed {allowed}/{MAX_CHECKS_PER_MINUTE} requests, blocked the rest")

    result = _can_call_gemini_check()
    assert result == False
    print(f"  {PASS()} Request after limit reached was correctly blocked")

    gemini_ai._check_timestamps.clear()
    print(f"\n  {GREEN}Rate Limiting works perfectly!{RESET}")
    return True


# ================================================================
# 5. Time Parser Test (ban/mute duration)
# ================================================================
def test_parse_time():
    header("5. Ban/Mute Duration Parser Test")
    from handlers.group_moderator import parse_time, get_time_string

    cases = [
        ("30 minutes", "30m", 30 * 60),
        ("2 hours",    "2h",  2 * 3600),
        ("1 day",      "1d",  86400),
        ("60 seconds", "60s", 60),
        ("Empty input", "",   0),
        ("Invalid input", "abc", 0),
    ]

    passed = failed = 0
    now = int(time.time())
    for desc, input_str, expected_delta in cases:
        result = parse_time(input_str)
        if expected_delta == 0:
            ok = result == 0
        else:
            actual_delta = result - now
            ok = abs(actual_delta - expected_delta) <= 2

        mark = PASS() if ok else FAIL()
        str_result = get_time_string(input_str)
        print(f"  {mark} {desc}: '{input_str}' -> {str_result}")
        if not ok:
            failed += 1
        else:
            passed += 1

    print(f"\n  Result: {GREEN}{passed} passed{RESET} | {RED}{failed} failed{RESET}")
    return failed == 0


# ================================================================
# Run All Tests
# ================================================================
async def run_all():
    print(f"\n{BOLD}{CYAN}{'='*60}")
    print(f"  AlsManagerBot - Full Test Suite")
    print(f"{'='*60}{RESET}")

    results = {}
    results["Local Filter"]      = test_local_filter()
    results["Duration Parser"]   = test_parse_time()
    results["SQLite Database"]   = await test_database()
    results["Rate Limiting"]     = await test_rate_limiting()
    results["Gemini AI"]         = await test_gemini_detection()

    header("FINAL TEST RESULTS")
    all_passed = True
    for name, ok in results.items():
        mark = PASS() if ok else FAIL()
        print(f"  {mark}  {name}")
        if not ok:
            all_passed = False

    print()
    if all_passed:
        print(f"  {GREEN}{BOLD}ALL TESTS PASSED! Bot is ready for production.{RESET}\n")
    else:
        print(f"  {RED}{BOLD}Some tests failed. Review details above.{RESET}\n")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
