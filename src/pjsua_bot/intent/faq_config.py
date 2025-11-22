"""FAQ configuration for intent classification - Persian/Farsi FAQs."""

from typing import Any, Dict

# FAQ structure with Persian FAQs
FAQS: Dict[str, Dict[str, Any]] = {
    "slow_computer": {
        "keywords": [
            # Persian keywords - ordered by specificity (more specific first)
            "کامپیوترم کند است",
            "کامپیوتر کند است",
            "کامپیوتر کند",
            "کامپیوترم کند",
            "کند کار می کند",
            "کند کار میکند",
            "کند است",
            "کند",
            "رم",
            "کمبود رم",
            "حافظه",
            "startup",
            "برنامه های startup",
            "برنامه‌های startup",
            "malware",
            "بدافزار",
            "دیسک",
            "پاکسازی",
            "پاکسازی دیسک",
            "برنامه",
            "برنامه های غیرضروری",
            "برنامه‌های غیرضروری",
            "سیستم عامل",
            "سیستم‌عامل",
            "آنتی ویروس",
            "آنتی‌ویروس",
            "به روزرسانی",
            "به‌روزرسانی",
            "آپدیت",
            "ارتقا",
            "ارتقا رم",
            # English alternatives (if users mix languages)
            "slow",
            "computer slow",
            "ram",
            "memory",
        ],
        "questions": [
            "چرا کامپیوترم کند کار می کند؟",
            "کامپیوترم کند است",
            "کامپیوتر کند کار می کند",
            "کمبود رم دارم",
            "برنامه های startup زیاد دارم",
        ],
        "response_text": (
            "علت اغلب کمبود رم، برنامه های startup زیاد یا malware است. "
            "دیسک را پاکسازی کنید، برنامه های غیرضروری را ببندید، "
            "سیستم عامل و آنتی ویروس را به روزرسانی کنید و رم را ارتقا دهید."
        ),
        "response_audio": "assets/audio/faq_slow_computer.wav",  # Optional
        "priority": 1,
    },
    "computer_shuts_down": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "کامپیوترم ناگهان خاموش می شود",
            "کامپیوتر ناگهان خاموش می شود",
            "کامپیوترم خاموش می شود",
            "کامپیوتر خاموش می شود",
            "ناگهان خاموش",
            "خاموش می شود",
            "خاموش میشود",
            "خاموش",
            "گرد و غبار",
            "گردوغبار",
            "فن",
            "فن ها",
            "فن‌ها",
            "گرمای بیش از حد",
            "گرما",
            "گرم",
            "تمیز",
            "تمیز کردن",
            "تمیزکردن",
            "جریان هوا",
            "جریان‌هوا",
            "سخت افزار",
            "سخت‌افزار",
            # English alternatives
            "shutdown",
            "turns off",
            "fan",
            "dust",
            "overheating",
            "hardware",
        ],
        "questions": [
            "کامپیوترم ناگهان خاموش می شود",
            "کامپیوتر خاموش می شود",
            "فن کامپیوتر مشکل دارد",
            "کامپیوتر گرم می شود",
        ],
        "response_text": (
            "معمولاً به دلیل گرد و غبار در فن ها یا گرمای بیش از حد است. "
            "فنها را تمیز کنید، جریان هوا را بررسی کنید و اگر ادامه داشت، "
            "سخت افزار را چک کنید."
        ),
        "response_audio": "assets/audio/faq_computer_shuts_down.wav",  # Optional
        "priority": 2,
    },
    "screen_freezes": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "صفحه نمایش کامپیوترم فریز می شود",
            "صفحه نمایش کامپیوتر فریز می شود",
            "صفحه نمایش فریز می شود",
            "برنامه گیر کرده",
            "برنامه گیرکرده",
            "برنامه‌های گیرکرده",
            "صفحه فریز شده",
            "کامپیوتر فریز می کند",
            "فریز می شود",
            "فریز میشود",
            "صفحه نمایش",
            "صفحه‌نمایش",
            "فریز",
            "Manager Task",
            "Task Manager",
            "تسک منیجر",
            "برنامه",
            "برنامه های گیرکرده",
            "برنامه‌های گیرکرده",
            "ریستارت",
            "ریست",
            "راه‌اندازی مجدد",
            "نرمافزار",
            "نرم‌افزار",
            "به روزرسانی",
            "به‌روزرسانی",
            "تکرار",
            "جلوگیری",
            # English alternatives
            "freeze",
            "frozen",
            "screen freeze",
            "task manager",
            "restart",
        ],
        "questions": [
            "صفحه نمایش کامپیوترم فریز می شود",
            "صفحه فریز شده",
            "کامپیوتر فریز می کند",
            "برنامه گیر کرده",
        ],
        "response_text": (
            "از Manager Task برای بستن برنامه های گیرکرده استفاده کنید یا "
            "سیستم را ریستارت کنید. نرمافزارها را به روزرسانی کنید تا از "
            "تکرار جلوگیری شود."
        ),
        "response_audio": "assets/audio/faq_screen_freezes.wav",  # Optional
        "priority": 3,
    },
    "blue_screen": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "صفحه آبی مرگ ظاهر می شود",
            "صفحه آبی مرگ",
            "صفحه آبی",
            "صفحه‌آبی",
            "BSOD",
            "Blue Screen",
            "کد خطا",
            "کد‌خطا",
            "درایور",
            "درایورها",
            "به روزرسانی",
            "به‌روزرسانی",
            "اسکن",
            "اسکن سیستم",
            "سخت افزار",
            "سخت‌افزار",
            "تکنسین",
            "تعمیرکار",
            # English alternatives
            "blue screen",
            "bsod",
            "error code",
            "driver",
            "hardware",
        ],
        "questions": [
            "صفحه آبی مرگ ظاهر می شود",
            "BSOD دارم",
            "صفحه آبی می بینم",
            "کد خطا دارم",
        ],
        "response_text": (
            "کد خطا را یادداشت کنید، درایورها را به روزرسانی کنید و سیستم را "
            "اسکن کنید. اگر سخت افزاری باشد، به تکنسین مراجعه کنید."
        ),
        "response_audio": "assets/audio/faq_blue_screen.wav",  # Optional
        "priority": 4,
    },
    "slow_internet": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "اینترنت کند کار می کند",
            "اینترنت کند کار میکند",
            "اینترنت من کند است",
            "اینترنت کند",
            "اینترنت من کند",
            "اینترنت",
            "کند است",
            "کند",
            "کش",
            "کش مرورگر",
            "کش‌مرورگر",
            "مرورگر",
            "بروزر",
            "پاک",
            "پاک کردن",
            "پاککردن",
            "اکستنشن",
            "اکستنشن های غیرضروری",
            "اکستنشن‌های غیرضروری",
            "روتر",
            "مودم",
            "ریستارت",
            "ریست",
            "سرعت",
            "سرعت اینترنت",
            "تست سرعت",
            "ISP",
            "سرویس دهنده",
            # English alternatives
            "internet slow",
            "slow internet",
            "browser cache",
            "router",
            "speed",
        ],
        "questions": [
            "اینترنت من کند است",
            "سرعت اینترنت کم است",
            "اینترنت کند کار می کند",
            "مشکل اینترنت دارم",
        ],
        "response_text": (
            "کش مرورگر را پاک کنید، اکستنشنهای غیرضروری را غیرفعال کنید و روتر را "
            "ریستارت کنید. سرعت را تست کنید و با ISP تماس بگیرید."
        ),
        "response_audio": "assets/audio/faq_slow_internet.wav",  # Optional
        "priority": 5,
    },
    "default": {
        "keywords": [],
        "questions": [],
        "response_text": (
            "متشکرم از تماس شما. لطفاً برای اطلاعات بیشتر به وب‌سایت ما مراجعه کنید "
            "یا با نماینده ما صحبت کنید."
        ),
        "response_audio": None,
        "priority": 0,
    },
}
