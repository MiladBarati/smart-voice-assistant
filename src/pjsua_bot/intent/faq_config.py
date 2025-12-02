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
    "forgot_login_password": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "پسورد ورودم را فراموش کردم",
            "پسورد ورود را فراموش کردم",
            "پسورد را فراموش کردم",
            "رمز ورود را فراموش کردم",
            "رمز ورودم را فراموش کردم",
            "پسورد فراموش",
            "رمز فراموش",
            "فراموشی پسورد",
            "فراموشی رمز",
            "recovery",
            "ریست پسورد",
            "ریست رمز",
            "password manager",
            "مدیریت پسورد",
            "IT",
            # English alternatives
            "forgot password",
            "password recovery",
            "reset password",
        ],
        "questions": [
            "پسورد ورودم را فراموش کردم",
            "رمز ورود را فراموش کرده‌ام",
            "چطور پسورد را ریست کنم",
        ],
        "response_text": (
            "از گزینه recovery یا تماس با IT برای ریست استفاده کنید. "
            "از password manager برای آینده بهره ببرید."
        ),
        "response_audio": "assets/audio/faq_forgot_login_password.wav",
        "priority": 6,
    },
    "forgot_chargooneh_password": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "رمز اتوماسیون اداری چارگون را فراموش کرده‌ام",
            "رمز چارگون را فراموش کردم",
            "رمز اتوماسیون چارگون",
            "چارگون",
            "اتوماسیون اداری",
            "سامانه چارگون",
            "فراموشی رمز عبور چارگون",
            "فراموشی رمز چارگون",
            "کد ملی",
            "شماره پرسنلی",
            "رمز موقت",
            "موبایل",
            # English alternatives
            "chargooneh",
            "office automation",
        ],
        "questions": [
            "رمز اتوماسیون اداری چارگون را فراموش کرده‌ام",
            "رمز چارگون را فراموش کردم",
            "چطور رمز چارگون را ریست کنم",
        ],
        "response_text": (
            "به سامانه چارگون بروید → «فراموشی رمز عبور» → کد ملی و شماره پرسنلی بزنید "
            "تا رمز موقت به موبایلتان بیاید."
        ),
        "response_audio": "assets/audio/faq_forgot_chargooneh_password.wav",
        "priority": 7,
    },
    "forgot_my_nicico_password": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "رمز ورود به سامانه مس من را فراموش کرده‌ام",
            "رمز my.nicico.com را فراموش کردم",
            "رمز سامانه مس من",
            "سامانه مس من",
            "my.nicico.com",
            "مس من",
            "فراموشی رمز مس من",
            "فراموشی رمز",
            "کد پرسنلی",
            "ایمیل شرکتی",
            "موبایل",
            "رمز جدید",
            # English alternatives
            "my nicico",
            "nicico",
        ],
        "questions": [
            "رمز ورود به سامانه مس من (my.nicico.com) را فراموش کرده‌ام",
            "رمز مس من را فراموش کردم",
            "چطور رمز سامانه مس من را ریست کنم",
        ],
        "response_text": (
            "روی «فراموشی رمز» کلیک کنید و کد پرسنلی وارد کنید؛ "
            "رمز جدید به ایمیل شرکتی یا موبایل می‌آید."
        ),
        "response_audio": "assets/audio/faq_forgot_my_nicico_password.wav",
        "priority": 8,
    },
    "forgot_inventory_password": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "رمز مدیریت کالا را فراموش کرده‌ام",
            "رمز مدیریت کالا",
            "مدیریت کالا",
            "سیستم مدیریت کالا",
            "فراموشی رمز مدیریت کالا",
            "تیکت",
            "واحد مدیریت کالا",
            "ریست رمز",
            "ریست پسورد",
            # English alternatives
            "inventory",
            "inventory management",
        ],
        "questions": [
            "رمز مدیریت کالا را فراموش کرده‌ام",
            "رمز سیستم مدیریت کالا را فراموش کردم",
            "چطور رمز مدیریت کالا را ریست کنم",
        ],
        "response_text": ("تیکت به واحد مدیریت کالا بزنید تا رمز را ریست کنند."),
        "response_audio": "assets/audio/faq_forgot_inventory_password.wav",
        "priority": 9,
    },
    "user_account_locked": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "کاربر قفل شده و نمی‌توانم لاگین کنم",
            "اکانت قفل شده",
            "کاربر قفل شده",
            "قفل شده",
            "نمی‌توانم لاگین کنم",
            "لاگین نمی‌شود",
            "اکانت من قفل است",
            "پس از ۱۵ دقیقه",
            "خودبه‌خود باز می‌شود",
            "تیکت",
            "IT",
            "آنلاک",
            "باز کردن اکانت",
            # English alternatives
            "account locked",
            "user locked",
            "cannot login",
            "unlock",
        ],
        "questions": [
            "کاربر قفل شده و نمی‌توانم لاگین کنم",
            "اکانت من قفل است",
            "چطور اکانت قفل شده را باز کنم",
        ],
        "response_text": (
            "بعد از ۱۵ دقیقه خودبه‌خود باز می‌شود؛ در غیر این صورت تیکت بزنید "
            "تا IT آنلاک کند."
        ),
        "response_audio": "assets/audio/faq_user_account_locked.wav",
        "priority": 10,
    },
    "system_off_domain": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "سیستم از دامین خارج شده و با یوزر لوکال بالا می‌آید",
            "سیستم از دامین خارج شده",
            "دامین خارج شده",
            "یوزر لوکال",
            "کاربر لوکال",
            "کابل شبکه",
            "کابل شبکه را چک کنید",
            "ریستارت",
            "حساب دامین",
            "لاگین دامین",
            "جوین دامین",
            "دامین",
            "domain",
            "تیکت",
            "IT",
            # English alternatives
            "off domain",
            "local user",
            "network cable",
            "join domain",
        ],
        "questions": [
            "سیستم از دامین خارج شده و با یوزر لوکال بالا می‌آید",
            "کامپیوتر از دامین خارج شده",
            "چطور سیستم را به دامین برگردانم",
        ],
        "response_text": (
            "کابل شبکه را چک کنید، سپس سیستم را ریستارت کنید و "
            "با حساب دامین لاگین کنید؛ "
            "اگر نشد تیکت بزنید تا دوباره جوین دامین شود."
        ),
        "response_audio": "assets/audio/faq_system_off_domain.wav",
        "priority": 11,
    },
    "usb_port_blocked": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "پورت USB روی کامپیوترم بسته است و فلش شناسایی نمی‌شود",
            "پورت USB بسته است",
            "USB بسته",
            "فلش شناسایی نمی‌شود",
            "فلش کار نمی‌کند",
            "USB کار نمی‌کند",
            "سیاست سازمانی USB",
            "پورت USB",
            "USB",
            "فلش",
            "تیکت",
            "IT",
            "باز کردن پورت",
            "موقت",
            "دائم",
            # English alternatives
            "USB blocked",
            "USB port blocked",
            "USB disabled",
            "flash drive",
        ],
        "questions": [
            "پورت USB روی کامپیوترم بسته است و فلش شناسایی نمی‌شود",
            "USB کار نمی‌کند",
            "فلش من شناسایی نمی‌شود",
        ],
        "response_text": (
            "سیاست سازمانی USB را بسته؛ تیکت بزنید تا IT به‌صورت موقت یا دائم "
            "پورت شما را باز کند."
        ),
        "response_audio": "assets/audio/faq_usb_port_blocked.wav",
        "priority": 12,
    },
    "windows_login_freeze": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "صفحه ورود ویندوز گیر می‌کند",
            "صفحه ورود گیر می‌کند",
            "صفحه لاگین گیر می‌کند",
            "ویندوز گیر می‌کند",
            "Safe Mode",
            "بوت Safe Mode",
            "درایورها",
            "به‌روزرسانی درایور",
            "System Restore",
            "ریستور سیستم",
            "صفحه ورود",
            "لاگین",
            "گیر می‌کند",
            "فریز",
            # English alternatives
            "login freeze",
            "windows login",
            "safe mode",
            "system restore",
            "driver update",
        ],
        "questions": [
            "صفحه ورود ویندوز گیر می‌کند",
            "صفحه لاگین گیر کرده",
            "ویندوز در صفحه ورود فریز می‌شود",
        ],
        "response_text": (
            "در Safe Mode بوت کنید، درایورها را به‌روزرسانی کنید یا از "
            "System Restore استفاده کنید."
        ),
        "response_audio": "assets/audio/faq_windows_login_freeze.wav",
        "priority": 13,
    },
    "slow_computer_general": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "چرا کامپیوترم کند کار می‌کند",
            "کامپیوترم کند کار می‌کند",
            "کامپیوتر کند کار می‌کند",
            "کامپیوتر کند",
            "کند کار می‌کند",
            "کند کار میکند",
            "کمبود رم",
            "برنامه‌های startup",
            "برنامه های startup",
            "startup",
            "malware",
            "بدافزار",
            "دیسک",
            "پاکسازی دیسک",
            "پاکسازی",
            "برنامه‌های غیرضروری",
            "برنامه های غیرضروری",
            "سیستم‌عامل",
            "سیستم عامل",
            "آنتی‌ویروس",
            "آنتی ویروس",
            "به‌روزرسانی",
            "به روزرسانی",
            "ارتقا رم",
            "ارتقا",
            # English alternatives
            "slow computer",
            "computer slow",
            "low ram",
            "memory",
        ],
        "questions": [
            "چرا کامپیوترم کند کار می‌کند؟",
            "کامپیوترم کند است",
            "کامپیوتر کند کار می‌کند",
        ],
        "response_text": (
            "علت اغلب کمبود رم، برنامه‌های startup زیاد یا malware است. "
            "دیسک را پاکسازی کنید، برنامه‌های غیرضروری را ببندید، "
            "سیستم‌عامل و آنتی‌ویروس را به‌روزرسانی کنید و رم را ارتقا دهید."
        ),
        "response_audio": "assets/audio/faq_slow_computer_general.wav",
        "priority": 14,
    },
    "laptop_overheating": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "لپ‌تاپم سریع داغ می‌کند",
            "لپتاپم سریع داغ می‌کند",
            "لپ‌تاپ داغ می‌شود",
            "لپتاپ داغ می‌شود",
            "لپ‌تاپ داغ",
            "لپتاپ داغ",
            "داغ می‌شود",
            "داغ میشود",
            "گرم می‌شود",
            "گرم میشود",
            "فن‌ها",
            "فن ها",
            "تمیز کردن فن",
            "سطح صاف",
            "برنامه‌های سنگین",
            "برنامه های سنگین",
            "پد خنک‌کننده",
            "پد خنک کننده",
            "خنک‌کننده",
            "خنک کننده",
            # English alternatives
            "laptop overheating",
            "laptop hot",
            "overheating",
            "cooling pad",
        ],
        "questions": [
            "چرا لپ‌تاپم سریع داغ می‌کند؟",
            "لپ‌تاپم خیلی داغ می‌شود",
            "لپ‌تاپ داغ می‌کند",
        ],
        "response_text": (
            "فن‌ها را تمیز کنید، روی سطح صاف استفاده کنید و "
            "برنامه‌های سنگین را محدود کنید. "
            "اگر ادامه داشت، پد خنک‌کننده بخرید."
        ),
        "response_audio": "assets/audio/faq_laptop_overheating.wav",
        "priority": 15,
    },
    "computer_shuts_down_general": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "کامپیوترم ناگهان خاموش می‌شود",
            "کامپیوتر ناگهان خاموش می‌شود",
            "کامپیوترم خاموش می‌شود",
            "کامپیوتر خاموش می‌شود",
            "ناگهان خاموش",
            "خاموش می‌شود",
            "خاموش میشود",
            "گرد و غبار",
            "گردوغبار",
            "فن‌ها",
            "فن ها",
            "گرمای بیش از حد",
            "گرما",
            "تمیز کردن فن",
            "جریان هوا",
            "جریان‌هوا",
            "سخت‌افزار",
            "سخت افزار",
            # English alternatives
            "computer shuts down",
            "turns off",
            "dust",
            "fan",
            "overheating",
            "hardware",
        ],
        "questions": [
            "کامپیوترم ناگهان خاموش می‌شود، چه کنم؟",
            "کامپیوتر ناگهان خاموش می‌شود",
            "کامپیوترم خودش خاموش می‌شود",
        ],
        "response_text": (
            "معمولاً به دلیل گرد و غبار در فن‌ها یا گرمای بیش از حد است. "
            "فن‌ها را تمیز کنید، جریان هوا را بررسی کنید و اگر ادامه داشت، "
            "سخت‌افزار را چک کنید."
        ),
        "response_audio": "assets/audio/faq_computer_shuts_down.wav",
        "priority": 16,
    },
    "loud_fan_noise": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "صدای فن کامپیوتر خیلی بلند است",
            "صدای فن بلند است",
            "فن خیلی بلند",
            "فن صدا می‌دهد",
            "فن صدا میدهد",
            "صدای فن",
            "گرد و غبار",
            "گردوغبار",
            "تمیز کردن فن",
            "BIOS",
            "سرعت فن",
            "کاهش سرعت فن",
            "تعویض فن",
            "فن",
            # English alternatives
            "loud fan",
            "fan noise",
            "fan sound",
            "fan speed",
        ],
        "questions": [
            "صدای فن کامپیوتر خیلی بلند است",
            "فن کامپیوترم خیلی صدا می‌دهد",
            "صدای فن خیلی بلند است",
        ],
        "response_text": (
            "گرد و غبار را تمیز کنید، سرعت فن را در BIOS کاهش دهید یا فن را تعویض کنید."
        ),
        "response_audio": "assets/audio/faq_loud_fan_noise.wav",
        "priority": 17,
    },
    "windows_update_slow": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "سیستم بعد از آپدیت ویندوز کند شده",
            "بعد از آپدیت ویندوز کند شده",
            "آپدیت ویندوز کند",
            "ویندوز آپدیت",
            "آپدیت ویندوز",
            "pause آپدیت",
            "موقتاً pause",
            "درایورها",
            "rollback درایور",
            "rollback",
            "فضای دیسک",
            "آزاد کردن فضا",
            "کند شده",
            "کند",
            # English alternatives
            "windows update",
            "update slow",
            "driver rollback",
            "disk space",
        ],
        "questions": [
            "سیستم بعد از آپدیت ویندوز کند شده",
            "بعد از آپدیت کند شده",
            "آپدیت ویندوز سیستم را کند کرده",
        ],
        "response_text": (
            "آپدیت‌ها را موقتاً pause کنید، درایورها را rollback کنید و "
            "فضای دیسک را آزاد کنید."
        ),
        "response_audio": "assets/audio/faq_windows_update_slow.wav",
        "priority": 18,
    },
    "laptop_battery_drains_fast": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "باتری لپ‌تاپ زود خالی می‌شود",
            "باتری لپتاپ زود خالی می‌شود",
            "باتری زود خالی می‌شود",
            "باتری زود خالی میشود",
            "باتری خالی می‌شود",
            "زود خالی می‌شود",
            "روشنایی صفحه",
            "روشنایی",
            "برنامه‌های پس‌زمینه",
            "برنامه های پس‌زمینه",
            "پس‌زمینه",
            "کالیبره کردن باتری",
            "کالیبره باتری",
            "کالیبره",
            "باتری",
            # English alternatives
            "battery drains fast",
            "battery dies quickly",
            "battery calibration",
            "background apps",
        ],
        "questions": [
            "چرا باتری لپ‌تاپ زود خالی می‌شود؟",
            "باتری لپ‌تاپم خیلی زود خالی می‌شود",
            "باتری زود تمام می‌شود",
        ],
        "response_text": (
            "روشنایی صفحه را کم کنید، برنامه‌های پس‌زمینه را ببندید و "
            "باتری را کالیبره کنید."
        ),
        "response_audio": "assets/audio/faq_laptop_battery_drains_fast.wav",
        "priority": 19,
    },
    "project_crashes": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "پروژه‌هایم در نرم‌افزار کرش می‌کند",
            "پروژه‌هایم کرش می‌کند",
            "پروژه کرش می‌کند",
            "کرش می‌کند",
            "کرش میکند",
            "ذخیره نمی‌شود",
            "ذخیره نمیشود",
            "Auto-Save",
            "auto save",
            "فعال کردن Auto-Save",
            "فایل با نام جدید",
            "ذخیره با نام جدید",
            "رم",
            "بررسی رم",
            "پروژه",
            # English alternatives
            "project crashes",
            "crashes",
            "not saving",
            "auto save",
        ],
        "questions": [
            "پروژه‌هایم در نرم‌افزار کرش می‌کند و ذخیره نمی‌شود",
            "پروژه‌ام کرش می‌کند",
            "نرم‌افزار کرش می‌کند و ذخیره نمی‌شود",
        ],
        "response_text": (
            "Auto-Save را فعال کنید، فایل را با نام جدید ذخیره کنید و رم را بررسی کنید."
        ),
        "response_audio": "assets/audio/faq_project_crashes.wav",
        "priority": 20,
    },
    "software_crashes": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "نرم‌افزارها مدام کرش می‌کنند",
            "نرم‌افزارها کرش می‌کنند",
            "نرم‌افزار کرش می‌کند",
            "مدام کرش می‌کند",
            "کرش می‌کند",
            "کرش میکند",
            "به‌روزرسانی نرم‌افزار",
            "به روزرسانی نرم‌افزار",
            "reinstall",
            "نصب مجدد",
            "سازگاری",
            "چک کردن سازگاری",
            "نسخه جایگزین",
            "جایگزین",
            # English alternatives
            "software crashes",
            "crashes",
            "reinstall",
            "compatibility",
        ],
        "questions": [
            "نرم‌افزارها مدام کرش می‌کنند",
            "نرم‌افزارم کرش می‌کند",
            "برنامه‌ها کرش می‌کنند",
        ],
        "response_text": (
            "نرم‌افزارها را به‌روزرسانی یا reinstall کنید و سازگاری را چک کنید. "
            "اگر ادامه داشت، از نسخه جایگزین استفاده کنید."
        ),
        "response_audio": "assets/audio/faq_software_crashes.wav",
        "priority": 21,
    },
    "screen_freezes_general": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "صفحه نمایش کامپیوترم فریز می‌شود",
            "صفحه نمایش فریز می‌شود",
            "صفحه فریز می‌شود",
            "فریز می‌شود",
            "فریز میشود",
            "Task Manager",
            "تسک منیجر",
            "برنامه‌های گیرکرده",
            "برنامه های گیرکرده",
            "برنامه گیر کرده",
            "ریستارت",
            "ریست",
            "به‌روزرسانی نرم‌افزار",
            "به روزرسانی نرم‌افزار",
            "صفحه نمایش",
            "صفحه‌نمایش",
            "فریز",
            # English alternatives
            "screen freezes",
            "freeze",
            "frozen",
            "task manager",
        ],
        "questions": [
            "صفحه نمایش کامپیوترم فریز می‌شود",
            "صفحه فریز می‌شود",
            "کامپیوتر فریز می‌کند",
        ],
        "response_text": (
            "از Task Manager برای بستن برنامه‌های گیرکرده استفاده کنید یا "
            "سیستم را ریستارت کنید. نرم‌افزارها را به‌روزرسانی کنید تا "
            "از تکرار جلوگیری شود."
        ),
        "response_audio": "assets/audio/faq_screen_freezes.wav",
        "priority": 22,
    },
    "slow_internet_general": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "اینترنت من کند است",
            "اینترنت کند است",
            "اینترنت کند",
            "کند است",
            "کند",
            "کش مرورگر",
            "کش‌مرورگر",
            "پاک کردن کش",
            "اکستنشن‌های غیرضروری",
            "اکستنشن های غیرضروری",
            "اکستنشن",
            "غیرفعال کردن اکستنشن",
            "روتر",
            "ریستارت روتر",
            "ریست روتر",
            "سرعت",
            "تست سرعت",
            "ISP",
            "سرویس دهنده",
            "اینترنت",
            # English alternatives
            "slow internet",
            "internet slow",
            "browser cache",
            "router",
            "speed test",
        ],
        "questions": [
            "اینترنت من کند است",
            "سرعت اینترنت کم است",
            "اینترنت کند کار می‌کند",
        ],
        "response_text": (
            "کش مرورگر را پاک کنید، اکستنشن‌های غیرضروری را غیرفعال کنید و "
            "روتر را ریستارت کنید. سرعت را تست کنید و با ISP تماس بگیرید."
        ),
        "response_audio": "assets/audio/faq_slow_internet.wav",
        "priority": 23,
    },
    "wifi_disconnects": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "اتصال وای‌فای قطع می‌شود",
            "وای‌فای قطع می‌شود",
            "وایفای قطع می‌شود",
            "وای‌فای قطع",
            "وایفای قطع",
            "قطع می‌شود",
            "قطع میشود",
            "روتر",
            "ریستارت روتر",
            "ریستارت کامپیوتر",
            "ریستارت",
            "تنظیمات شبکه",
            "شبکه",
            "درایورهای وای‌فای",
            "درایور وای‌فای",
            "به‌روزرسانی درایور",
            "وای‌فای",
            "وایفای",
            # English alternatives
            "wifi disconnects",
            "wifi drops",
            "wifi connection",
            "network settings",
            "wifi driver",
        ],
        "questions": [
            "اتصال وای‌فای قطع می‌شود",
            "وای‌فای من قطع می‌شود",
            "اتصال وای‌فای مدام قطع می‌شود",
        ],
        "response_text": (
            "روتر و کامپیوتر را ریستارت کنید، تنظیمات شبکه را بررسی کنید و "
            "درایورهای وای‌فای را به‌روزرسانی کنید."
        ),
        "response_audio": "assets/audio/faq_wifi_disconnects.wav",
        "priority": 24,
    },
    "company_network_issue": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "نمی‌توانم به شبکه شرکتی وصل شوم",
            "شبکه شرکتی وصل نمی‌شود",
            "شبکه شرکتی",
            "شبکه شرکت",
            "VPN",
            "چک کردن VPN",
            "credentials",
            "اعتبارنامه",
            "تأیید credentials",
            "IT",
            "دسترسی",
            "تنظیمات جدید",
            "شبکه",
            "وصل نمی‌شود",
            "وصل نمیشود",
            # English alternatives
            "company network",
            "corporate network",
            "vpn",
            "credentials",
            "network access",
        ],
        "questions": [
            "نمی‌توانم به شبکه شرکتی وصل شوم",
            "شبکه شرکتی کار نمی‌کند",
            "به شبکه شرکت وصل نمی‌شوم",
        ],
        "response_text": (
            "VPN را چک کنید، credentials را تأیید کنید و با IT برای دسترسی یا "
            "تنظیمات جدید تماس بگیرید."
        ),
        "response_audio": "assets/audio/faq_company_network_issue.wav",
        "priority": 25,
    },
    "websites_not_loading": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "وب‌سایت‌ها در مرورگر باز نمی‌شوند",
            "وب‌سایت‌ها باز نمی‌شوند",
            "وبسایت‌ها باز نمی‌شوند",
            "سایت‌ها باز نمی‌شوند",
            "باز نمی‌شوند",
            "باز نمیشوند",
            "DNS",
            "تغییر DNS",
            "8.8.8.8",
            "کش",
            "پاک کردن کش",
            "فایروال",
            "آنتی‌ویروس",
            "غیرفعال کردن فایروال",
            "غیرفعال کردن آنتی‌ویروس",
            "مرورگر",
            "بروزر",
            # English alternatives
            "websites not loading",
            "sites not opening",
            "dns",
            "firewall",
            "antivirus",
        ],
        "questions": [
            "وب‌سایت‌ها در مرورگر باز نمی‌شوند",
            "سایت‌ها باز نمی‌شوند",
            "مرورگر سایت‌ها را باز نمی‌کند",
        ],
        "response_text": (
            "DNS را به 8.8.8.8 تغییر دهید، کش را پاک کنید و فایروال/آنتی‌ویروس را "
            "موقتاً غیرفعال کنید."
        ),
        "response_audio": "assets/audio/faq_websites_not_loading.wav",
        "priority": 26,
    },
    "shared_drive_access": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "نمی‌توانم به درایو اشتراکی دسترسی پیدا کنم",
            "درایو اشتراکی دسترسی ندارم",
            "درایو اشتراکی",
            "Shared Drive",
            "shared drive",
            "مجوزها",
            "مجوز",
            "چک کردن مجوز",
            "IT",
            "شبکه",
            "ریستارت شبکه",
            "مسیر درایو",
            "مپ کردن درایو",
            "مپ درایو",
            "دسترسی",
            "دسترسی ندارم",
            # English alternatives
            "shared drive",
            "network drive",
            "permissions",
            "map drive",
        ],
        "questions": [
            "نمی‌توانم به درایو اشتراکی (Shared Drive) دسترسی پیدا کنم",
            "درایو اشتراکی باز نمی‌شود",
            "به Shared Drive دسترسی ندارم",
        ],
        "response_text": (
            "مجوزها را با IT چک کنید، شبکه را ریستارت کنید و "
            "مسیر درایو را دوباره مپ کنید."
        ),
        "response_audio": "assets/audio/faq_shared_drive_access.wav",
        "priority": 27,
    },
    "voip_not_working": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "سیستم تلفنی من کار نمی‌کند",
            "تلفن کار نمی‌کند",
            "تلفن قطع و وصل می‌شود",
            "قطع و وصل می‌شود",
            "قطع و وصل",
            "تلفن",
            "پریز",
            "بکشید و بزنید",
            "شماره داخلی",
            "محل",
            "پشتیبانی VoIP",
            "VoIP",
            "voip",
            "سیستم تلفنی",
            "کار نمی‌کند",
            "کار نمیکند",
            # English alternatives
            "voip not working",
            "phone not working",
            "phone disconnects",
            "voip support",
        ],
        "questions": [
            "سیستم تلفنی من کار نمی‌کند یا قطع و وصل می‌شود",
            "تلفن من کار نمی‌کند",
            "تلفن قطع و وصل می‌شود",
        ],
        "response_text": (
            "تلفن را از پریز بکشید و دوباره بزنید؛ اگر مشکل حل نشد، "
            "شماره داخلی و محل خود را به پشتیبانی VoIP اعلام کنید."
        ),
        "response_audio": "assets/audio/faq_voip_not_working.wav",
        "priority": 28,
    },
    "cannot_share_wifi_password": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "نمی‌توانم رمز وای‌فای را به دیگران بدهم",
            "رمز وای‌فای را نمی‌دانم",
            "رمز وای‌فای",
            "رمز وایفای",
            "تنظیمات روتر",
            "روتر",
            "QR code",
            "QR کد",
            "فعال کردن QR code",
            "وای‌فای",
            "وایفای",
            "رمز",
            "پسورد",
            # English alternatives
            "wifi password",
            "wifi pass",
            "router settings",
            "qr code",
        ],
        "questions": [
            "نمی‌توانم رمز وای‌فای را به دیگران بدهم",
            "رمز وای‌فای را نمی‌دانم",
            "چطور رمز وای‌فای را ببینم",
        ],
        "response_text": (
            "رمز را از تنظیمات روتر ببینید یا QR code را در روتر فعال کنید."
        ),
        "response_audio": "assets/audio/faq_cannot_share_wifi_password.wav",
        "priority": 29,
    },
    "printer_not_working": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "پرینتر کار نمی‌کند",
            "پرینتر کار نمیکند",
            "پرینتر کار نمی کند",
            "پرینتر",
            "کار نمی‌کند",
            "کار نمیکند",
            "اتصالات",
            "چک کردن اتصالات",
            "درایورها",
            "به‌روزرسانی درایور",
            "به روزرسانی درایور",
            "صف چاپ",
            "پاک کردن صف چاپ",
            "جوهر",
            "سطح جوهر",
            "کاغذ",
            "سطح کاغذ",
            # English alternatives
            "printer not working",
            "printer",
            "print queue",
            "ink",
            "paper",
        ],
        "questions": [
            "پرینتر کار نمی‌کند",
            "پرینتر من کار نمی‌کند",
            "چرا پرینتر کار نمی‌کند",
        ],
        "response_text": (
            "اتصالات را چک کنید، درایورها را به‌روزرسانی کنید و صف چاپ را پاک کنید. "
            "سطح جوهر یا کاغذ را بررسی کنید."
        ),
        "response_audio": "assets/audio/faq_printer_not_working.wav",
        "priority": 30,
    },
    "scanner_not_working": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "نمی‌توانم از اسکنر استفاده کنم",
            "اسکنر کار نمی‌کند",
            "اسکنر کار نمیکند",
            "اسکنر",
            "استفاده از اسکنر",
            "درایور اسکنر",
            "reinstall درایور",
            "نصب مجدد درایور",
            "کابل‌ها",
            "کابل ها",
            "چک کردن کابل",
            "نرم‌افزار اسکن",
            "به‌روزرسانی نرم‌افزار",
            "به روزرسانی نرم‌افزار",
            # English alternatives
            "scanner not working",
            "scanner",
            "scanner driver",
            "reinstall",
        ],
        "questions": [
            "نمی‌توانم از اسکنر استفاده کنم",
            "اسکنر کار نمی‌کند",
            "اسکنر من کار نمی‌کند",
        ],
        "response_text": (
            "درایور اسکنر را reinstall کنید، کابل‌ها را چک کنید و نرم‌افزار اسکن را "
            "به‌روزرسانی کنید."
        ),
        "response_audio": "assets/audio/faq_scanner_not_working.wav",
        "priority": 31,
    },
    "fax_photocopy_issue": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "دستگاه فکس یا فتوکپی کار نمی‌کند",
            "دستگاه فکس کار نمی‌کند",
            "فتوکپی کار نمی‌کند",
            "فکس کار نمی‌کند",
            "دستگاه فکس",
            "دستگاه فتوکپی",
            "فکس",
            "فتوکپی",
            "خاموش/روشن",
            "خاموش و روشن",
            "ریستارت دستگاه",
            "کد خطا",
            "واحد تجهیزات اداری",
            "تعمیرکار",
            "کار نمی‌کند",
            "کار نمیکند",
            # English alternatives
            "fax not working",
            "photocopy not working",
            "fax machine",
            "photocopier",
            "error code",
        ],
        "questions": [
            "دستگاه فکس یا فتوکپی کار نمی‌کند",
            "فکس کار نمی‌کند",
            "دستگاه فتوکپی خطا می‌دهد",
        ],
        "response_text": (
            "ابتدا دستگاه را خاموش/روشن کنید؛ اگر خطا ادامه داشت، کد خطا را یادداشت و "
            "به واحد تجهیزات اداری اطلاع دهید تا تعمیرکار بفرستند."
        ),
        "response_audio": "assets/audio/faq_fax_photocopy_issue.wav",
        "priority": 32,
    },
    "request_peripheral_equipment": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "درخواست کابل پرینتر، ماوس، کیبورد یا تجهیزات جانبی دارم",
            "درخواست تجهیزات جانبی",
            "درخواست کابل",
            "درخواست ماوس",
            "درخواست کیبورد",
            "کابل پرینتر",
            "ماوس",
            "کیبورد",
            "تجهیزات جانبی",
            "سامانه تدارکات",
            "فرم آنلاین",
            "درخواست تجهیزات",
            "تأیید مدیر",
            "انبار",
            "حواله",
            "حضوری تحویل",
            # English alternatives
            "request equipment",
            "peripheral equipment",
            "cable",
            "mouse",
            "keyboard",
        ],
        "questions": [
            "درخواست کابل پرینتر، ماوس، کیبورد یا تجهیزات جانبی دارم",
            "چطور تجهیزات جانبی درخواست بدهم",
            "درخواست ماوس و کیبورد دارم",
        ],
        "response_text": (
            "در سامانه تدارکات (یا فرم آنلاین) درخواست تجهیزات بدهید؛ "
            "بعد از تأیید مدیر، انبار حواله می‌دهد و باید حضوری تحویل بگیرید."
        ),
        "response_audio": "assets/audio/faq_request_peripheral_equipment.wav",
        "priority": 33,
    },
    "keyboard_mouse_not_working": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "کیبورد یا موس کار نمی‌کند",
            "کیبورد کار نمی‌کند",
            "موس کار نمی‌کند",
            "ماوس کار نمی‌کند",
            "کیبورد",
            "موس",
            "ماوس",
            "کار نمی‌کند",
            "کار نمیکند",
            "اتصالات",
            "باتری‌ها",
            "باتری ها",
            "بررسی باتری",
            "درایورها",
            "reinstall درایور",
            "نصب مجدد درایور",
            "تست روی دستگاه دیگر",
            # English alternatives
            "keyboard not working",
            "mouse not working",
            "keyboard",
            "mouse",
            "battery",
            "reinstall driver",
        ],
        "questions": [
            "کیبورد یا موس کار نمی‌کند",
            "ماوس من کار نمی‌کند",
            "کیبورد کار نمی‌کند",
        ],
        "response_text": (
            "اتصالات یا باتری‌ها را بررسی کنید، درایورها را reinstall کنید و "
            "روی دستگاه دیگری تست کنید."
        ),
        "response_audio": "assets/audio/faq_keyboard_mouse_not_working.wav",
        "priority": 34,
    },
    "keyboard_keys_not_working": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "صفحه کلید بعضی کلیدها کار نمی‌کند",
            "بعضی کلیدهای کیبورد کار نمی‌کند",
            "کلیدهای کیبورد کار نمی‌کند",
            "کلید کار نمی‌کند",
            "صفحه کلید",
            "کیبورد",
            "کلید",
            "تمیز کردن کیبورد",
            "درایور",
            "reinstall درایور",
            "نصب مجدد درایور",
            "کیبورد خارجی",
            "وصل کردن کیبورد خارجی",
            "کار نمی‌کند",
            "کار نمیکند",
            # English alternatives
            "keyboard keys not working",
            "keys not working",
            "keyboard",
            "external keyboard",
            "clean keyboard",
        ],
        "questions": [
            "صفحه کلید بعضی کلیدها کار نمی‌کند",
            "بعضی کلیدهای کیبورد کار نمی‌کند",
            "کلیدهای کیبورد من کار نمی‌کند",
        ],
        "response_text": (
            "کیبورد را تمیز کنید، درایور را reinstall کنید یا کیبورد خارجی وصل کنید."
        ),
        "response_audio": "assets/audio/faq_keyboard_keys_not_working.wav",
        "priority": 35,
    },
    "usb_not_detected": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "USB وصل نمی‌شود",
            "USB شناسایی نمی‌شود",
            "USB کار نمی‌کند",
            "USB",
            "وصل نمی‌شود",
            "شناسایی نمی‌شود",
            "پورت‌های دیگر",
            "پورت های دیگر",
            "کامپیوتر دیگر",
            "امتحان کامپیوتر دیگر",
            "درایورهای USB",
            "درایور USB",
            "به‌روزرسانی درایور USB",
            "به روزرسانی درایور USB",
            "سخت‌افزاری",
            "سخت افزاری",
            "تعویض",
            # English alternatives
            "usb not detected",
            "usb not working",
            "usb port",
            "usb driver",
        ],
        "questions": [
            "USB وصل نمی‌شود",
            "USB من شناسایی نمی‌شود",
            "USB کار نمی‌کند",
        ],
        "response_text": (
            "پورت‌های دیگر یا کامپیوتر دیگری را امتحان کنید و درایورهای USB را "
            "به‌روزرسانی کنید. اگر سخت‌افزاری باشد، تعویض کنید."
        ),
        "response_audio": "assets/audio/faq_usb_not_detected.wav",
        "priority": 36,
    },
    "cannot_copy_from_flash": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "نمی‌توانم از فلش‌درایو فایل کپی کنم",
            "از فلش کپی نمی‌شود",
            "فلش کپی نمی‌شود",
            "فلش‌درایو",
            "فلش درایو",
            "فلش",
            "کپی فایل",
            "کپی نمی‌شود",
            "تست در کامپیوتر دیگر",
            "کامپیوتر دیگر",
            "write-protection",
            "write protection",
            "بردارید write-protection",
            "فرمت",
            "فرمت کردن",
            # English alternatives
            "cannot copy from flash",
            "flash drive",
            "usb drive",
            "write protection",
            "format",
        ],
        "questions": [
            "نمی‌توانم از فلش‌درایو فایل کپی کنم",
            "از فلش کپی نمی‌شود",
            "فلش من کپی نمی‌شود",
        ],
        "response_text": (
            "فلش را در کامپیوتر دیگری تست کنید، write-protection را بردارید یا "
            "فرمت کنید."
        ),
        "response_audio": "assets/audio/faq_cannot_copy_from_flash.wav",
        "priority": 37,
    },
    "excel_word_not_opening": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "فایل اکسل یا ورد باز نمی‌شود",
            "فایل اکسل باز نمی‌شود",
            "فایل ورد باز نمی‌شود",
            "اکسل باز نمی‌شود",
            "ورد باز نمی‌شود",
            "اکسل",
            "ورد",
            "Word",
            "Excel",
            "Office",
            "نسخه دیگر Office",
            "Repair",
            "نصب مجدد",
            "فرمت فایل",
            "بررسی فرمت",
            "باز نمی‌شود",
            "باز نمیشود",
            # English alternatives
            "excel not opening",
            "word not opening",
            "office file",
            "repair office",
        ],
        "questions": [
            "فایل اکسل یا ورد باز نمی‌شود",
            "اکسل باز نمی‌شود",
            "فایل ورد من باز نمی‌شود",
        ],
        "response_text": (
            "فایل را با نسخه دیگر Office باز کنید یا از Repair در نصب مجدد "
            "استفاده کنید. فرمت فایل را بررسی کنید."
        ),
        "response_audio": "assets/audio/faq_excel_word_not_opening.wav",
        "priority": 38,
    },
    "pdf_not_opening": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "فایل PDF باز نمی‌شود یا خراب است",
            "PDF باز نمی‌شود",
            "فایل PDF خراب است",
            "PDF خراب",
            "PDF",
            "Adobe Reader",
            "Adobe",
            "Reader جدید",
            "نسخه جدید",
            "دانلود از منبع دیگر",
            "منبع دیگر",
            "باز نمی‌شود",
            "خراب است",
            # English alternatives
            "pdf not opening",
            "pdf corrupted",
            "adobe reader",
            "pdf file",
        ],
        "questions": [
            "فایل PDF باز نمی‌شود یا خراب است",
            "PDF من باز نمی‌شود",
            "فایل PDF خراب است",
        ],
        "response_text": (
            "از Adobe Reader جدید استفاده کنید یا فایل را از منبع دیگری دانلود کنید."
        ),
        "response_audio": "assets/audio/faq_pdf_not_opening.wav",
        "priority": 39,
    },
    "cannot_install_software": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "نمی‌توانم برنامه جدیدی نصب کنم",
            "نصب برنامه",
            "نصب نمی‌شود",
            "نصب نمیشود",
            "فضای دیسک",
            "الزامات سیستم",
            "سیستم requirements",
            "آنتی‌ویروس",
            "خاموش کردن آنتی‌ویروس",
            "موقتاً خاموش",
            "فایل نصب",
            "دانلود مجدد",
            "نصب",
            "برنامه",
            # English alternatives
            "cannot install software",
            "installation failed",
            "disk space",
            "system requirements",
            "antivirus",
        ],
        "questions": [
            "نمی‌توانم برنامه جدیدی نصب کنم",
            "نصب برنامه کار نمی‌کند",
            "برنامه نصب نمی‌شود",
        ],
        "response_text": (
            "فضای دیسک و الزامات سیستم را چک کنید، آنتی‌ویروس را موقتاً خاموش کنید و "
            "فایل نصب را دوباره دانلود کنید."
        ),
        "response_audio": "assets/audio/faq_cannot_install_software.wav",
        "priority": 40,
    },
    "blue_screen_general": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "صفحه آبی مرگ (BSOD) ظاهر می‌شود",
            "صفحه آبی مرگ ظاهر می‌شود",
            "صفحه آبی مرگ",
            "صفحه آبی",
            "صفحه‌آبی",
            "BSOD",
            "Blue Screen",
            "کد خطا",
            "کد‌خطا",
            "یادداشت کد خطا",
            "درایورها",
            "به‌روزرسانی درایور",
            "به روزرسانی درایور",
            "اسکن سیستم",
            "اسکن",
            "سخت‌افزاری",
            "سخت افزاری",
            "تکنسین",
            "تعمیرکار",
            # English alternatives
            "blue screen",
            "bsod",
            "blue screen of death",
            "error code",
            "driver",
            "hardware",
        ],
        "questions": [
            "صفحه آبی مرگ (BSOD) ظاهر می‌شود",
            "BSOD دارم",
            "صفحه آبی می بینم",
        ],
        "response_text": (
            "کد خطا را یادداشت کنید، درایورها را به‌روزرسانی کنید و سیستم را اسکن کنید. "
            "اگر سخت‌افزاری باشد، به تکنسین مراجعه کنید."
        ),
        "response_audio": "assets/audio/faq_blue_screen.wav",
        "priority": 41,
    },
    "virus_malware_infection": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "ویروس یا malware به سیستمم نفوذ کرده",
            "ویروس به سیستم نفوذ کرده",
            "malware به سیستم نفوذ کرده",
            "ویروس",
            "malware",
            "بدافزار",
            "نفوذ",
            "آنتی‌ویروس",
            "نصب آنتی‌ویروس",
            "اسکن کامل",
            "اسکن",
            "سیستم‌عامل",
            "سیستم عامل",
            "به‌روزرسانی سیستم‌عامل",
            "به روزرسانی سیستم عامل",
            "دانلودهای مشکوک",
            "دانلود مشکوک",
            "اجتناب از دانلود",
            # English alternatives
            "virus",
            "malware",
            "infection",
            "antivirus",
            "scan",
        ],
        "questions": [
            "ویروس یا malware به سیستمم نفوذ کرده",
            "سیستمم ویروس دارد",
            "بدافزار به سیستم نفوذ کرده",
        ],
        "response_text": (
            "آنتی‌ویروس نصب کنید، اسکن کامل انجام دهید و سیستم‌عامل را به‌روزرسانی کنید. "
            "از دانلودهای مشکوک اجتناب کنید."
        ),
        "response_audio": "assets/audio/faq_virus_malware_infection.wav",
        "priority": 42,
    },
    "antivirus_alerts": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "برنامه آنتی‌ویروس مدام هشدار می‌دهد",
            "آنتی‌ویروس مدام هشدار می‌دهد",
            "آنتی‌ویروس هشدار می‌دهد",
            "هشدار آنتی‌ویروس",
            "هشدار مدام",
            "آنتی‌ویروس",
            "اسکن کامل",
            "اسکن",
            "whitelist",
            "برنامه‌های معتبر",
            "برنامه های معتبر",
            "اضافه کردن به whitelist",
            "به‌روزرسانی آنتی‌ویروس",
            "به روزرسانی آنتی‌ویروس",
            # English alternatives
            "antivirus alerts",
            "antivirus warnings",
            "antivirus",
            "whitelist",
            "scan",
        ],
        "questions": [
            "برنامه آنتی‌ویروس مدام هشدار می‌دهد",
            "آنتی‌ویروس خیلی هشدار می‌دهد",
            "هشدارهای آنتی‌ویروس زیاد است",
        ],
        "response_text": (
            "اسکن کامل انجام دهید، whitelist برنامه‌های معتبر را اضافه کنید و "
            "آنتی‌ویروس را به‌روزرسانی کنید."
        ),
        "response_audio": "assets/audio/faq_antivirus_alerts.wav",
        "priority": 43,
    },
    "no_sound": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "صدا از کامپیوترم نمی‌آید",
            "صدا نمی‌آید",
            "صدا نمیاید",
            "صدا",
            "صوتی",
            "تنظیمات صدا",
            "موت",
            "mute",
            "چک کردن موت",
            "درایورهای صوتی",
            "درایور صوتی",
            "به‌روزرسانی درایور صوتی",
            "به روزرسانی درایور صوتی",
            "reinstall درایور",
            "نصب مجدد درایور",
            # English alternatives
            "no sound",
            "no audio",
            "sound not working",
            "audio driver",
            "mute",
        ],
        "questions": [
            "صدا از کامپیوترم نمی‌آید",
            "کامپیوترم صدا ندارد",
            "صدا کار نمی‌کند",
        ],
        "response_text": (
            "تنظیمات صدا را چک کنید (موت نباشد) و درایورهای صوتی را به‌روزرسانی یا "
            "reinstall کنید."
        ),
        "response_audio": "assets/audio/faq_no_sound.wav",
        "priority": 44,
    },
    "display_issue": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "مشکل نمایشگر دارم (تصویر سیاه یا اعوجاج)",
            "مشکل نمایشگر",
            "تصویر سیاه",
            "اعوجاج",
            "نمایشگر",
            "مانیتور",
            "کابل‌ها",
            "کابل ها",
            "چک کردن کابل",
            "درایورهای گرافیک",
            "درایور گرافیک",
            "به‌روزرسانی درایور گرافیک",
            "به روزرسانی درایور گرافیک",
            "تست روی دستگاه دیگر",
            "مانیتور دیگر",
            # English alternatives
            "display issue",
            "monitor problem",
            "black screen",
            "distortion",
            "graphics driver",
        ],
        "questions": [
            "مشکل نمایشگر دارم (تصویر سیاه یا اعوجاج)",
            "نمایشگر مشکل دارد",
            "تصویر مانیتور سیاه است",
        ],
        "response_text": (
            "کابل‌ها را چک کنید، درایورهای گرافیک را به‌روزرسانی کنید و "
            "مانیتور را روی دستگاه دیگری تست کنید."
        ),
        "response_audio": "assets/audio/faq_display_issue.wav",
        "priority": 45,
    },
    "second_monitor_not_detected": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "مانیتور دوم وصل نمی‌شود",
            "مانیتور دوم شناسایی نمی‌شود",
            "مانیتور دوم",
            "مانیتور اضافی",
            "وصل نمی‌شود",
            "شناسایی نمی‌شود",
            "کابل",
            "پورت",
            "چک کردن کابل",
            "چک کردن پورت",
            "رزولوشن",
            "تنظیم رزولوشن",
            "درایور گرافیک",
            "به‌روزرسانی درایور گرافیک",
            "به روزرسانی درایور گرافیک",
            "مانیتور",
            # English alternatives
            "second monitor",
            "monitor not detected",
            "display not working",
            "graphics driver",
            "resolution",
        ],
        "questions": [
            "مانیتور دوم وصل نمی‌شود",
            "مانیتور دوم شناسایی نمی‌شود",
            "مانیتور اضافی کار نمی‌کند",
        ],
        "response_text": (
            "کابل و پورت را چک کنید، رزولوشن را تنظیم کنید و درایور گرافیک را "
            "به‌روزرسانی کنید."
        ),
        "response_audio": "assets/audio/faq_second_monitor_not_detected.wav",
        "priority": 46,
    },
    "chargooneh_attach_file": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "چطور فایل را در اتوماسیون اداری چارگون پیوست کنم",
            "پیوست فایل در چارگون",
            "پیوست فایل چارگون",
            "اتوماسیون اداری چارگون",
            "چارگون",
            "پیوست فایل",
            "نامه جدید",
            "بارگذاری فایل",
            "آپلود فایل",
            "تیک سبز",
            "فایل",
            "پیوست",
            # English alternatives
            "chargooneh",
            "attach file",
            "file upload",
        ],
        "questions": [
            "چطور فایل را در اتوماسیون اداری چارگون پیوست کنم؟",
            "چطور در چارگون فایل پیوست کنم",
            "پیوست فایل در چارگون",
        ],
        "response_text": (
            "در نامه جدید روی «پیوست فایل» کلیک کنید → فایل را از کامپیوتر "
            "انتخاب کنید → صبر کنید تا بارگذاری کامل شود و تیک سبز بخورد."
        ),
        "response_audio": "assets/audio/faq_chargooneh_attach_file.wav",
        "priority": 47,
    },
    "chargooneh_increase_upload_limit": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "چطور حجم آپلود در اتوماسیون اداری چارگون را افزایش دهم",
            "افزایش حجم آپلود چارگون",
            "حجم آپلود چارگون",
            "سقف آپلود",
            "افزایش سقف آپلود",
            "۱۰ مگ",
            "۵۰ مگ",
            "اتوماسیون اداری چارگون",
            "چارگون",
            "واحد IT مرکزی",
            "IT مرکزی",
            "تیکت",
            "آپلود",
            # English alternatives
            "chargooneh",
            "upload limit",
            "increase upload",
        ],
        "questions": [
            "چطور حجم آپلود در اتوماسیون اداری چارگون را افزایش دهم؟",
            "سقف آپلود چارگون را چطور افزایش دهم",
            "حجم آپلود چارگون کم است",
        ],
        "response_text": (
            "این تنظیم توسط واحد IT مرکزی انجام می‌شود؛ تیکت بزنید تا سقف آپلود شما را "
            "از ۱۰ مگ به ۵۰ مگ افزایش دهند."
        ),
        "response_audio": "assets/audio/faq_chargooneh_increase_upload_limit.wav",
        "priority": 48,
    },
    "nextcloud_upload_issue": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "نمی‌توانم فایل را در فضای ابری نکسکلود آپلود کنم",
            "فایل در نکسکلود آپلود نمی‌شود",
            "نکسکلود آپلود نمی‌شود",
            "فضای ابری نکسکلود",
            "نکسکلود",
            "Nextcloud",
            "nextcloud",
            "حجم فایل",
            "حداکثر ۲ گیگ",
            "۲ گیگ",
            "کش مرورگر",
            "پاک کردن کش",
            "مرورگر کروم",
            "مرورگر فایرفاکس",
            "کروم",
            "فایرفاکس",
            "آپلود",
            "آپلود نمی‌شود",
            # English alternatives
            "nextcloud",
            "upload issue",
            "file upload",
            "browser cache",
        ],
        "questions": [
            "چرا نمی‌توانم فایل را در فضای ابری نکسکلود آپلود کنم؟",
            "نکسکلود آپلود نمی‌شود",
            "فایل در نکسکلود آپلود نمی‌شود",
        ],
        "response_text": (
            "حجم فایل را چک کنید (حداکثر ۲ گیگ)، کش مرورگر را پاک کنید و از مرورگر "
            "کروم/فایرفاکس به‌روز استفاده کنید."
        ),
        "response_audio": "assets/audio/faq_nextcloud_upload_issue.wav",
        "priority": 49,
    },
    "nextcloud_how_to_use": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "نحوه صحیح استفاده از فضای ابری نکسکلود چیست",
            "چطور از نکسکلود استفاده کنم",
            "استفاده از نکسکلود",
            "فضای ابری نکسکلود",
            "نکسکلود",
            "Nextcloud",
            "nextcloud",
            "nextcloud.nicico.com",
            "نام کاربری",
            "رمز دامین",
            "لاگین",
            "پوشه",
            "درگ‌اند‌دراپ",
            "drag and drop",
            "فایل",
            # English alternatives
            "nextcloud",
            "how to use",
            "nextcloud.nicico.com",
            "login",
        ],
        "questions": [
            "نحوه صحیح استفاده از فضای ابری نکسکلود چیست؟",
            "چطور از نکسکلود استفاده کنم",
            "نکسکلود چطور کار می‌کند",
        ],
        "response_text": (
            "به آدرس nextcloud.nicico.com بروید، با نام کاربری و رمز دامین لاگین کنید، "
            "پوشه مورد نظر را انتخاب و فایل را درگ‌اند‌دراپ کنید."
        ),
        "response_audio": "assets/audio/faq_nextcloud_how_to_use.wav",
        "priority": 50,
    },
    "hard_drive_full": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "فضای هارد دیسکم پر شده",
            "هارد دیسک پر شده",
            "هارد پر شده",
            "فضای دیسک پر",
            "دیسک پر",
            "فضا پر",
            "فایل‌های غیرضروری",
            "فایل های غیرضروری",
            "حذف فایل",
            "فضای ابری",
            "ارتقا هارد",
            "هارد دیسک",
            "هارد",
            "دیسک",
            "فضا",
            # English alternatives
            "hard drive full",
            "disk full",
            "storage full",
            "cloud storage",
        ],
        "questions": [
            "فضای هارد دیسکم پر شده",
            "هارد دیسک من پر است",
            "فضای دیسک کم است",
        ],
        "response_text": (
            "فایل‌های غیرضروری را حذف کنید، از فضای ابری استفاده کنید یا "
            "هارد را ارتقا دهید."
        ),
        "response_audio": "assets/audio/faq_hard_drive_full.wav",
        "priority": 51,
    },
    "file_recovery": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "فایل‌هایم را از دست دادم، چطور بازیابی کنم",
            "فایل‌هایم را از دست دادم",
            "بازیابی فایل",
            "فایل از دست رفته",
            "Recycle Bin",
            "سطل بازیافت",
            "چک کردن Recycle Bin",
            "نرم‌افزارهای recovery",
            "recovery",
            "بازیابی",
            "بک‌آپ",
            "backup",
            "بک‌آپ منظم",
            "فایل",
            "از دست رفته",
            # English alternatives
            "file recovery",
            "lost files",
            "recycle bin",
            "recovery software",
            "backup",
        ],
        "questions": [
            "فایل‌هایم را از دست دادم، چطور بازیابی کنم؟",
            "فایل از دست رفته را چطور بازیابی کنم",
            "فایل حذف شده را چطور برگردانم",
        ],
        "response_text": (
            "Recycle Bin را چک کنید یا از نرم‌افزارهای recovery استفاده کنید. "
            "همیشه بک‌آپ منظم بگیرید."
        ),
        "response_audio": "assets/audio/faq_file_recovery.wav",
        "priority": 52,
    },
    "external_hard_not_detected": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "چرا هارد اکسترنال شناسایی نمی‌شود",
            "هارد اکسترنال شناسایی نمی‌شود",
            "هارد اکسترنال کار نمی‌کند",
            "هارد اکسترنال",
            "هارد خارجی",
            "شناسایی نمی‌شود",
            "پورت",
            "کابل",
            "عوض کردن پورت",
            "عوض کردن کابل",
            "Disk Management",
            "disk management",
            "فرمت",
            "چک کردن فرمت",
            "درایور",
            "نصب درایور",
            # English alternatives
            "external hard drive",
            "external hdd",
            "not detected",
            "disk management",
            "driver",
        ],
        "questions": [
            "چرا هارد اکسترنال شناسایی نمی‌شود",
            "هارد اکسترنال من کار نمی‌کند",
            "هارد خارجی شناسایی نمی‌شود",
        ],
        "response_text": (
            "پورت و کابل را عوض کنید، در Disk Management فرمت را چک کنید و "
            "درایور را نصب کنید."
        ),
        "response_audio": "assets/audio/faq_external_hard_not_detected.wav",
        "priority": 53,
    },
    "email_not_sending_or_receiving": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "ایمیل ارسال یا دریافت نمی‌شود",
            "ایمیل ارسال نمی‌شود",
            "ایمیل دریافت نمی‌شود",
            "ایمیل ارسال نمیشود",
            "ایمیل دریافت نمیشود",
            "ایمیل",
            "ارسال نمی‌شود",
            "دریافت نمی‌شود",
            "تنظیمات سرور",
            "سرور",
            "اینترنت",
            "چک کردن اینترنت",
            "credentials",
            "اعتبارنامه",
            "تأیید credentials",
            "ارائه‌دهنده",
            "ارائه دهنده",
            # English alternatives
            "email not sending",
            "email not receiving",
            "email server",
            "credentials",
        ],
        "questions": [
            "ایمیل ارسال یا دریافت نمی‌شود",
            "ایمیل من ارسال نمی‌شود",
            "ایمیل دریافت نمی‌شود",
        ],
        "response_text": (
            "تنظیمات سرور و اینترنت را چک کنید، credentials را تأیید کنید و با "
            "ارائه‌دهنده تماس بگیرید."
        ),
        "response_audio": "assets/audio/faq_email_not_sending_or_receiving.wav",
        "priority": 54,
    },
    "emails_going_to_spam": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "چرا ایمیل‌هایم به اسپم می‌روند",
            "ایمیل‌هایم به اسپم می‌رود",
            "ایمیل به اسپم می‌رود",
            "اسپم",
            "spam",
            "تنظیمات spam filter",
            "spam filter",
            "فیلتر اسپم",
            "Safe List",
            "safe list",
            "اضافه کردن به Safe List",
            "فرستنده",
            "IT",
            "هماهنگ با IT",
            "ایمیل",
            # English alternatives
            "emails going to spam",
            "spam filter",
            "safe list",
        ],
        "questions": [
            "چرا ایمیل‌هایم به اسپم می‌روند؟",
            "ایمیل‌هایم به اسپم می‌رود",
            "ایمیل به spam می‌رود",
        ],
        "response_text": (
            "تنظیمات spam filter را چک کنید، فرستنده را به Safe List اضافه کنید و "
            "با IT هماهنگ کنید."
        ),
        "response_audio": "assets/audio/faq_emails_going_to_spam.wav",
        "priority": 55,
    },
    "email_storage_full": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "حجم ایمیل من پر شده، چطور حجمش را افزایش دهم",
            "حجم ایمیل پر شده",
            "ایمیل پر شده",
            "حجم ایمیل",
            "ایمیل‌های قدیمی",
            "ایمیل های قدیمی",
            "حذف ایمیل قدیمی",
            "پیوست‌ها",
            "پیوست ها",
            "حذف پیوست",
            "تیکت",
            "IT",
            "سقف جیمیل",
            "سقف اوت‌لوک",
            "Gmail",
            "Outlook",
            "افزایش سقف",
            "افزایش حجم",
            "ایمیل",
            # English alternatives
            "email storage full",
            "email quota",
            "gmail",
            "outlook",
        ],
        "questions": [
            "حجم ایمیل من پر شده، چطور حجمش را افزایش دهم؟",
            "ایمیل من پر است",
            "حجم ایمیل کم است",
        ],
        "response_text": (
            "ایمیل‌های قدیمی و پیوست‌ها را حذف کنید یا تیکت بزنید تا IT سقف "
            "جیمیل/اوت‌لوک شما را موقتاً افزایش دهد."
        ),
        "response_audio": "assets/audio/faq_email_storage_full.wav",
        "priority": 56,
    },
    "no_audio_video_in_meetings": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "برنامه Teams یا Zoom صدا/تصویر ندارد",
            "Teams صدا ندارد",
            "Zoom صدا ندارد",
            "Teams تصویر ندارد",
            "Zoom تصویر ندارد",
            "Teams",
            "Zoom",
            "صدا ندارد",
            "تصویر ندارد",
            "میکروفون",
            "دوربین",
            "تنظیمات میکروفون",
            "تنظیمات دوربین",
            "درایورها",
            "به‌روزرسانی درایور",
            "به روزرسانی درایور",
            "ریستارت برنامه",
            "ریستارت",
            "جلسات آنلاین",
            "جلسه آنلاین",
            # English alternatives
            "teams no audio",
            "zoom no video",
            "microphone",
            "camera",
            "driver",
        ],
        "questions": [
            "برنامه Teams یا Zoom صدا/تصویر ندارد",
            "Teams من صدا ندارد",
            "Zoom تصویر ندارد",
        ],
        "response_text": (
            "میکروفون/دوربین را در تنظیمات چک کنید، درایورها را به‌روزرسانی کنید و "
            "برنامه را ریستارت کنید."
        ),
        "response_audio": "assets/audio/faq_no_audio_video_in_meetings.wav",
        "priority": 57,
    },
    "system_not_booting": {
        "keywords": [
            # Persian keywords - ordered by specificity
            "سیستم بوت نمی‌شود",
            "سیستم بوت نمیشود",
            "بوت نمی‌شود",
            "بوت نمیشود",
            "سیستم بالا نمی‌آید",
            "سیستم بالا نمیاید",
            "بالا نمی‌آید",
            "اتصالات",
            "چک کردن اتصالات",
            "Safe Mode",
            "safe mode",
            "بوت در Safe Mode",
            "ابزارهای recovery",
            "recovery",
            "OS",
            "reinstall OS",
            "نصب مجدد OS",
            "سیستم",
            "کامپیوتر",
            # English alternatives
            "system not booting",
            "computer not starting",
            "safe mode",
            "recovery",
            "reinstall os",
        ],
        "questions": [
            "سیستم بوت نمی‌شود",
            "کامپیوتر بالا نمی‌آید",
            "سیستم من بوت نمی‌شود",
        ],
        "response_text": (
            "اتصالات را چک کنید، در Safe Mode بوت کنید یا از ابزارهای recovery "
            "استفاده کنید. اگر لازم، OS را reinstall کنید."
        ),
        "response_audio": "assets/audio/faq_system_not_booting.wav",
        "priority": 58,
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


def get_faq_system_prompt(faqs: Dict[str, Dict[str, Any]] | None = None) -> str:
    """Generate system prompt for Ollama to classify intents.

    Args:
        faqs: FAQ configuration dict. If None, uses default FAQS.

    Returns:
        Formatted system prompt string that instructs Ollama to return intent names
    """
    if faqs is None:
        faqs = FAQS

    prompt_parts = [
        (
            "You are an intent classifier. Analyze user questions and "
            "classify them into one of the following intents."
        ),
        "You must respond with ONLY a JSON object in this exact format:",
        '{"intent": "intent_name"}',
        "",
        "Available intents:",
        "",
    ]

    # List all available intents with their keywords/questions
    intent_descriptions = []
    for intent_name, faq_config in faqs.items():
        if intent_name == "default":
            continue

        questions = faq_config.get("questions", [])
        keywords = faq_config.get("keywords", [])

        description_parts = [f"  - {intent_name}:"]
        if questions:
            description_parts.append(
                f"    Example questions: {', '.join(questions[:3])}"
            )
        if keywords:
            description_parts.append(f"    Keywords: {', '.join(keywords[:5])}")

        intent_descriptions.append("\n".join(description_parts))

    prompt_parts.extend(intent_descriptions)
    prompt_parts.append("")
    prompt_parts.append(
        'If the question does not match any intent, return: {"intent": "default"}'
    )
    prompt_parts.append("")
    prompt_parts.append(
        "IMPORTANT: Respond with ONLY the JSON object. "
        "Do not include any other text or explanation."
    )

    return "\n".join(prompt_parts)
