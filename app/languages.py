"""Per-language and per-dialect voice profiles.

Every profile here was drafted without native-speaker review. Each one is
marked ``needs_native_review=True`` and must be checked by at least two native
speakers of that exact variety before launch (see README, "Native review").

The profiles are guidance for the model, not a dictionary. They describe how
people actually greet, soften requests, show respect and joke, and list the
mistakes that make text sound machine-translated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

ARABIC = "arabic"
LATIN = "latin"

TONES: dict[str, str] = {
    "casual": "Relaxed, everyday texting between people who know each other. Short, natural, contractions and common slang are fine.",
    "friendly": "Warm and kind, like writing to a friend or a friendly colleague. Include the small courtesies a native would add.",
    "formal": "Respectful and polished, for elders, officials, clients or a boss. Use the honorifics and polite forms natives use, without sounding stiff or bureaucratic.",
    "playful": "Light, witty and teasing in a good-natured way, the humour a native would actually use. Never mocking, never crude.",
}

AUDIENCES: dict[str, str] = {
    "unknown": "The addressee is unknown. Use the form natives default to in that situation, and keep gendered forms to a minimum where the language allows.",
    "man": "Addressing one man. Use masculine forms where the language marks gender.",
    "woman": "Addressing one woman. Use feminine forms where the language marks gender.",
    "group": "Addressing a group of people. Use plural forms.",
}


@dataclass(frozen=True)
class Example:
    source: str
    target: str
    note: str
    target_latin: str = ""  # Latin-letter version for dialects that offer it


@dataclass(frozen=True)
class Idiom:
    expression: str
    meaning: str
    use: str


@dataclass(frozen=True)
class LanguageProfile:
    code: str
    name: str
    native_name: str
    region: str
    bcp47: str
    scripts: tuple[str, ...]
    default_script: str
    voice: str
    greetings: tuple[str, ...]
    politeness: tuple[str, ...]
    idioms: tuple[Idiom, ...]
    avoid: tuple[str, ...]
    examples: tuple[Example, ...]
    resource_level: str  # "lower" or "higher": how much good text the model has likely seen
    weak_spots: str
    latin_conventions: str = ""
    needs_native_review: bool = True
    reviewed_by: tuple[str, ...] = field(default_factory=tuple)

    def direction(self, script: str) -> str:
        return "rtl" if script == ARABIC else "ltr"

    def lang_tag(self, script: str) -> str:
        if script == LATIN and ARABIC in self.scripts:
            return f"{self.bcp47}-Latn"
        return self.bcp47

    def public(self) -> dict:
        """What the browser needs. No prompt material beyond what is shown."""
        return {
            "code": self.code,
            "name": self.name,
            "native_name": self.native_name,
            "region": self.region,
            "scripts": list(self.scripts),
            "default_script": self.default_script,
            "directions": {s: self.direction(s) for s in self.scripts},
            "lang_tags": {s: self.lang_tag(s) for s in self.scripts},
            "needs_native_review": self.needs_native_review,
            "resource_level": self.resource_level,
            "weak_spots": self.weak_spots,
        }

    def as_dict(self) -> dict:
        return asdict(self)


ARABIZI = (
    "Write Arabic the way people text it in Latin letters: 3 = ع, 7 = ح, 9 = ق (Morocco) "
    "or 2 = ء/ق-as-glottal-stop (Egypt, Levant), 5 or kh = خ, gh = غ, sh/ch = ش. "
    "Use the spelling habits of this region, not a scholarly transliteration."
)

REGION_ORDER = ("West Africa", "North Africa", "Gulf", "Levant", "East Africa", "Europe")

_PROFILES: tuple[LanguageProfile, ...] = (
    # ------------------------------------------------------------------ West Africa
    LanguageProfile(
        code="ha",
        name="Hausa",
        native_name="Hausa",
        region="West Africa",
        bcp47="ha",
        scripts=(LATIN,),
        default_script=LATIN,
        voice=(
            "Northern Nigerian / Niger Hausa as written in standard Boko (Latin) script. Greetings are "
            "layered and unhurried; asking after the family, work and health is normal before business. "
            "Religious blessings (mostly Islamic) are woven into everyday speech."
        ),
        greetings=(
            "Sannu (hello; also 'sorry/well done' when someone is working or hurt)",
            "Ina kwana? (good morning, lit. how did you sleep?) - reply: Lafiya lau",
            "Ina wuni? (daytime greeting) / Barka da yamma (good evening)",
            "Assalamu alaikum - reply: Wa alaikumus salam",
            "Ya gida? / Ya iyali? (how is home / the family?) - reply: Lafiya",
        ),
        politeness=(
            "Address older men as Malam, Baba or Alhaji (if he has made the pilgrimage) and older women as Hajiya or Mama; never by bare first name.",
            "'Don Allah' softens requests (please, lit. for God's sake); 'Na gode' is thanks; 'Yi haƙuri' is a polite apology or 'please bear with me'.",
            "Second person is gendered: ka (to a man), ki (to a woman), ku (plural, also used for extra respect in some contexts).",
            "Go round before direct requests: greet, ask after well-being, then ask.",
        ),
        idioms=(
            Idiom("Allah ya kiyaye", "May God protect (us)", "Reacting to bad news or a near miss."),
            Idiom("Allah ya jiƙansa da rahama", "May God have mercy on him", "Condolences for a man who has died (jiƙanta for a woman)."),
            Idiom("Ba komai", "It's nothing / no problem", "Reassuring someone after an apology."),
            Idiom("Sai an jima", "See you later", "Casual goodbye."),
            Idiom("A hankali", "Gently / take it easy", "Advising caution or calm."),
        ),
        avoid=(
            "Dropping the hooked letters ɓ, ɗ, ƙ, ƴ: they change meaning; use them in standard spelling.",
            "Word-for-word English idioms (e.g. 'break a leg') that mean nothing in Hausa; use a blessing instead.",
            "Getting ka/ki (man/woman) wrong; when unknown, follow the audience rule.",
            "Over-formal, sermon-like religious phrasing in casual chat.",
        ),
        examples=(
            Example("Good morning sir, how is your family?", "Ina kwana, Malam. Ya iyali?", "Short, respectful, uses Malam rather than a literal 'sir'."),
            Example("I'm so sorry for your loss.", "Allah ya jiƙansa da rahama. Allah ya ba ku haƙurin rashinsa.", "Condolence as prayer, which is how it is said, not 'I am sorry'."),
            Example("Can you send me the report today, please?", "Don Allah, za ka iya turo min rahoton yau?", "'Don Allah' up front; ka assumes a male addressee."),
        ),
        resource_level="lower",
        weak_spots="Less high-quality Hausa text exists online than for French or Arabic; expect occasional unnatural word choice, wrong gender agreement or missing hooked letters. Regional differences (Kano vs Sokoto vs Niger) are not modelled.",
    ),
    LanguageProfile(
        code="yo",
        name="Yoruba",
        native_name="Yorùbá",
        region="West Africa",
        bcp47="yo",
        scripts=(LATIN,),
        default_script=LATIN,
        voice=(
            "Standard Yoruba (Nigeria) with full tone marks and under-dots. Respect for age is built into "
            "the grammar: the plural/honorific ẹ is used for elders and strangers, o/ìwọ only for peers and juniors. "
            "Greetings are situational: there is a greeting for almost every activity."
        ),
        greetings=(
            "Ẹ káàárọ̀ (good morning, respectful) / Káàárọ̀ (to a peer)",
            "Ẹ káàsán (good afternoon) / Ẹ kú ìrọ̀lẹ́ (good evening) / Ẹ káalẹ́ (good night)",
            "Ẹ kú iṣẹ́ (well done at work) - said to anyone working",
            "Ṣé dáadáa ni? (are you well?) - reply: Dáadáa ni",
        ),
        politeness=(
            "Use ẹ (honorific plural) for anyone older or senior; o for peers. Mixing them reads as rude or as a mistake.",
            "'Ẹ jọ̀ọ́' (please, respectful) vs 'Jọ̀ọ́' (casual); 'Ẹ ṣé' (thank you, respectful) vs 'O ṣé'.",
            "'Ẹ má bínú' is a respectful apology (lit. don't be angry).",
            "Add 'mà' (to a woman) or 'sà' (to a man) for extra respect, as in everyday Nigerian speech.",
        ),
        idioms=(
            Idiom("Ẹ kú ìrọ́jú", "Condolences / well done for enduring", "Said to the bereaved."),
            Idiom("Ọlọ́run á tù yín nínú", "God will comfort you", "Comforting the bereaved."),
            Idiom("Ó dàbọ̀", "Goodbye", "Neutral farewell."),
            Idiom("Kò burú", "It's not bad / that's fine", "Mild approval or acceptance."),
        ),
        avoid=(
            "Omitting tone marks and under-dots: without them many words are ambiguous. Always write them.",
            "Using o/ìwọ to an elder.",
            "Literal English politeness ('I would like to request') instead of Yoruba softeners.",
            "English proverbs translated literally; use a Yoruba equivalent only if one truly fits, otherwise plain speech.",
        ),
        examples=(
            Example("Good morning, ma.", "Ẹ káàárọ̀ mà.", "Respectful ẹ plus 'mà', which is how it is actually said."),
            Example("I'm so sorry for your loss.", "Ẹ kú ìrọ́jú o. Ọlọ́run á tù yín nínú.", "Situational condolence greeting plus a blessing."),
            Example("Please, can you send me the report today?", "Ẹ jọ̀ọ́, ṣé ẹ lè fi ìjábọ̀ náà ránṣẹ́ sí mi lónìí?", "Respectful ẹ throughout."),
        ),
        resource_level="lower",
        weak_spots="Tone marks are the biggest risk: the model may misplace or omit them, which can change meaning. Word choice for modern business terms is uncertain. Proverbs should be checked carefully; a wrong proverb is worse than none.",
    ),
    LanguageProfile(
        code="ig",
        name="Igbo",
        native_name="Igbo",
        region="West Africa",
        bcp47="ig",
        scripts=(LATIN,),
        default_script=LATIN,
        voice=(
            "Standard (Central) Igbo in Ọnwụ orthography with dotted vowels (ị, ọ, ụ) and ṅ. Warm, "
            "communal, rich in proverbs; elders and titles carry weight. Many speakers code-mix English."
        ),
        greetings=(
            "Ndewo (hello) / Kedu? (how are you?) - reply: Ọ dị mma",
            "Ụtụtụ ọma (good morning) / I bọọla chi? (did you wake well?)",
            "Ka ọ dị (bye, lit. let it be so) / Ka emesịa (see you later)",
        ),
        politeness=(
            "'Biko' is please; 'Daalụ' or 'Imela' is thank you.",
            "Address older men as Dede or Nna, older women as Daa or Nne; use titles (Chief, Ugo, Lolo) when known.",
            "'Ndo' means sorry, both apology and sympathy.",
            "Igbo pronouns do not mark gender, so the audience setting matters less than for Arabic or Hausa.",
        ),
        idioms=(
            Idiom("Onye aghala nwanne ya", "Let no one leave their sibling behind", "Solidarity, community appeals."),
            Idiom("Ndo, ka Chineke nye gị obi ike", "Sorry, may God give you strength (of heart)", "Condolences."),
            Idiom("Ọ dị mma", "It is fine / good", "Agreement or reassurance."),
        ),
        avoid=(
            "Dropping the dots on ị, ọ, ụ and ṅ; they are separate letters.",
            "Forcing proverbs into short or business messages.",
            "Literal English formality; Igbo politeness is shown with biko, titles and warmth.",
        ),
        examples=(
            Example("Good morning, how are you?", "Ụtụtụ ọma. Kedu ka ị mere?", "Natural pairing of greeting and well-being question."),
            Example("I'm so sorry for your loss.", "Ndo. Ka Chineke nye gị obi ike.", "Ndo plus a blessing, the usual shape."),
            Example("Please send me the report today.", "Biko, zitere m akụkọ ahụ taa.", "Biko up front; akụkọ is a broad word, natives may prefer the English 'report'."),
        ),
        resource_level="lower",
        weak_spots="One of the weakest languages here for the model. Dialects (Owerri, Onitsha, Nsukka and others) differ a lot and only a standard-ish variety is targeted. Expect English code-mixing choices and modern vocabulary to vary.",
    ),
    LanguageProfile(
        code="pcm",
        name="Nigerian Pidgin",
        native_name="Naijá",
        region="West Africa",
        bcp47="pcm",
        scripts=(LATIN,),
        default_script=LATIN,
        voice=(
            "Nigerian Pidgin as people text and speak it in Lagos, Warri and Port Harcourt: direct, expressive, "
            "humorous, with particles like o, sha, abi, sef. Spelling is informal and English-based."
        ),
        greetings=(
            "How far? - reply: I dey o / I dey kampe",
            "How you dey? / How body? / Wetin dey happen?",
            "Good morning o / Good evening sir",
        ),
        politeness=(
            "'Abeg' is please; 'Sorry o' or 'No vex' apologises; 'Thank you well well' is warm thanks.",
            "Respect comes from titles: Oga, Madam, Aunty, Uncle, Sir, Ma. Elders are still addressed with care even in Pidgin.",
            "Formal Pidgin exists (e.g. BBC Pidgin) but most people would write formal business messages in English; say so in explain if relevant.",
        ),
        idioms=(
            Idiom("No wahala", "No problem", "Agreeing or reassuring."),
            Idiom("Shine your eye", "Be alert / be smart", "Advice or warning."),
            Idiom("E don cast", "The secret is out / it's ruined", "Something has gone wrong or been revealed."),
            Idiom("Body no be firewood", "I'm human, I get tired", "Excusing yourself from too much work."),
        ),
        avoid=(
            "Writing English with a few Pidgin words sprinkled in: grammar must be Pidgin (dey, don, go, na, wetin).",
            "Exaggerated or comic 'stage Pidgin' that sounds like mockery.",
            "Using heavy slang in formal tone.",
        ),
        examples=(
            Example("Hi, how are you?", "How far? How you dey?", "The everyday opener."),
            Example("Sorry I'm late, the traffic was terrible.", "Abeg no vex, I late. Go-slow hold me well well.", "Go-slow is the Nigerian word for a traffic jam."),
            Example("Could you send the report today, please?", "Abeg, you fit send the report give me today?", "Pidgin grammar ('send ... give me')."),
        ),
        resource_level="lower",
        weak_spots="Spelling varies widely and there is little edited Pidgin text. Ghanaian and Cameroonian Pidgin are different and not covered. Fast-moving slang may be dated or wrong.",
    ),
    # ------------------------------------------------------------------ North Africa
    LanguageProfile(
        code="ary",
        name="Moroccan Darija",
        native_name="الدارجة المغربية",
        region="North Africa",
        bcp47="ary",
        scripts=(ARABIC, LATIN),
        default_script=ARABIC,
        voice=(
            "Moroccan Arabic as spoken in Casablanca/Rabat: fast, vowel-light, with French loanwords and "
            "some Amazigh vocabulary. Very different from Middle Eastern Arabic; many Moroccans text it in "
            "Latin letters with numbers."
        ),
        greetings=(
            "Salam / Salamu 3alaykum (سلام / السلام عليكم)",
            "Labas? / Labas 3lik? (لاباس؟) - reply: Labas, l7amdulillah",
            "Kidayr? (to a man) / Kidayra? (to a woman) (كيداير؟ / كيدايرة؟)",
            "Sba7 lkhir (صباح الخير) / Mssa lkhir (مسا الخير)",
        ),
        politeness=(
            "'3afak' (عافاك) or 'lla ykhallik' (الله يخليك) means please; 'Shukran' or 'Baraka llahu fik' thanks; 'Smeh liya' (سمح ليا) apologises.",
            "Address older men as 'Sidi' or 'Si + name' and older women as 'Lalla'; 'Khouya' (my brother) and 'Khti' (my sister) for peers.",
            "Gender: verbs and adjectives change for a woman (kidayra, nti); plural is ntuma.",
            "French words (merci, d'accord, normalement) are normal in casual and urban speech.",
        ),
        idioms=(
            Idiom("Ma kayn mushkil", "No problem", "Reassurance."),
            Idiom("Lah y3awnek", "May God help you", "Sympathy for someone with a lot to do."),
            Idiom("Bssa7tek", "To your health / enjoy", "When someone has something new or eats."),
            Idiom("Lah yr7mu", "May God have mercy on him", "Condolences."),
        ),
        avoid=(
            "Modern Standard Arabic words: kayfa 7aluk, madha, laysa, sawfa.",
            "Egyptian or Levantine words: ezzayak, kifak, shu, ana 3ayez, 7elw.",
            "Over-vocalised Arabic script with full harakat; Darija is written without them.",
            "Writing Darija Latin letters with a scholarly transliteration (ḥ, ʿ) instead of texting style (7, 3).",
        ),
        examples=(
            Example("Hi, how are you?", "سلام، لاباس عليك؟ كيداير؟", "Typical stacked greeting.", "Salam, labas 3lik? Kidayr?"),
            Example("Sorry I'm late, the traffic was terrible.", "سمح ليا، تعطلت، كان الزحام بزاف.", "Bzaf (a lot) is very Moroccan.", "Smeh liya, t3ettelt, kan zza7am bzaf."),
            Example("Could you please send the file today?", "عافاك، تقدر تصيفط ليا الفيشي اليوم؟", "Sifet = send; lfichi from French 'fichier'.", "3afak, t9der tsifet liya lfichi lyoum?"),
        ),
        resource_level="lower",
        weak_spots="The model has seen far more MSA and Egyptian than Darija, so MSA or Egyptian words may leak in. Regional Darija (north, east, south) and Amazigh-influenced speech are not modelled. Latin-letter spelling varies between people.",
        latin_conventions=ARABIZI + " Moroccans usually use 9 for ق, 3 for ع, 7 for ح, and ch or sh for ش.",
    ),
    LanguageProfile(
        code="arz",
        name="Egyptian Arabic",
        native_name="العامية المصرية",
        region="North Africa",
        bcp47="arz",
        scripts=(ARABIC, LATIN),
        default_script=ARABIC,
        voice=(
            "Cairene Egyptian Arabic: warm, witty, quick to joke, full of blessings and affectionate address. "
            "The most widely understood Arabic dialect thanks to film and TV."
        ),
        greetings=(
            "Ezzayak? (to a man) / Ezzayek? (to a woman) (إزيك؟) - reply: Kwayes/kwayesa, el7amdulillah",
            "3amel eh? / 3amla eh? (عامل إيه؟)",
            "Saba7 el-kheir (صباح الخير) - reply: Saba7 el-noor (صباح النور)",
            "Ahlan, nawwart (أهلاً، نورت) - welcoming someone",
        ),
        politeness=(
            "'Law sama7t' (to a man) / 'law sama7ti' (to a woman) (لو سمحت) and 'men fadlak' are please; 'Shukran' or 'Mersi' thanks.",
            "'7adretak' (حضرتك) is the respectful 'you' for elders, clients and strangers.",
            "Friendly address: ya basha, ya fandem, ya ostaz; elders: ya 7ag / ya 7agga; women peers: ya habibti.",
            "Softeners: momken (could you), ma3lesh (sorry / never mind).",
        ),
        idioms=(
            Idiom("El-ba2eya fe 7ayatak", "Condolences (lit. the rest [of life] is in your life)", "The standard condolence."),
            Idiom("Ma3lesh", "Never mind / sorry", "Light apology or comfort."),
            Idiom("Rabena yesahhel", "May God make it easy", "Wishing someone luck, or politely declining."),
            Idiom("Ya salam!", "Wow! / How lovely!", "Admiration or surprise."),
        ),
        avoid=(
            "MSA forms: hal, laysa, sawfa, madha, kayfa.",
            "Levantine or Gulf words: kifak, shu, wesh, abi.",
            "Writing ق as 2 in Arabic script; in Arabic script keep ق and rely on the reader's pronunciation; in Latin letters use 2.",
        ),
        examples=(
            Example("Hi, how are you?", "إزيك؟ عامل إيه؟", "Two quick questions, as Egyptians actually greet.", "Ezzayak? 3amel eh?"),
            Example("I'm so sorry for your loss.", "البقية في حياتك، ربنا يرحمه.", "Fixed condolence formula plus a prayer.", "El-ba2eya fe 7ayatak, rabena yer7amo."),
            Example("Could you please send me the report today?", "لو سمحت، ممكن تبعتلي التقرير النهارده؟", "Momken softens; naharda = today.", "Law sama7t, momken teb3atli el-ta2rir en-naharda?"),
        ),
        resource_level="higher",
        weak_spots="Usually the strongest Arabic dialect for the model, but it can still drift into MSA in formal tone. Upper Egyptian (Sa'idi) is not covered.",
        latin_conventions=ARABIZI + " Egyptians use 2 for the glottal stop (from ق), 3 for ع, 7 for ح, and g for ج.",
    ),
    # ------------------------------------------------------------------ Gulf
    LanguageProfile(
        code="ar-SA",
        name="Saudi Arabic",
        native_name="اللهجة السعودية",
        region="Gulf",
        bcp47="ar-SA",
        scripts=(ARABIC, LATIN),
        default_script=ARABIC,
        voice=(
            "Urban Saudi Arabic, Najdi (Riyadh) by default, understandable in Hijaz. Hospitable and generous in "
            "phrasing; religious formulas are common; respect for elders and status is explicit."
        ),
        greetings=(
            "Assalamu 3alaykum (السلام عليكم) - reply: Wa 3alaykum assalam",
            "Hala / Hala wallah / Ya hala (هلا / هلا والله)",
            "Wesh lonak? (Najdi, وش لونك؟) / Kef 7alak? (كيف حالك؟) - reply: Bkheir, el7amdulillah",
            "Sabah el-kheir (صباح الخير) - reply: Sabah el-noor",
        ),
        politeness=(
            "'Law sama7t' or 'law tikarramt' (لو تكرمت, if you would be so kind) are polite requests; 'Ya3teek el3afya' (يعطيك العافية) thanks someone for their effort.",
            "'Tal 3umrak' (طال عمرك, may your life be long) is used to elders, superiors and customers.",
            "Address men as 'Abu + son's name' or 'ya shaikh'; avoid addressing a woman you don't know by first name.",
            "Gender agreement matters (ent/enti, ta3al/ta3ali).",
        ),
        idioms=(
            Idiom("Abshir", "Consider it done", "Agreeing to a request, very common in service."),
            Idiom("3aẓẓam Allah ajrakum", "May God magnify your reward (condolence)", "Formal condolence; reply: shakar Allah sa3yakum."),
            Idiom("Ma 3alayk amr", "If it's no trouble", "Softening a request."),
            Idiom("Ya hala wallah", "Very warm welcome", "Greeting someone you're happy to see."),
        ),
        avoid=(
            "Egyptian or Levantine words: ezzayak, kifak, shu, 3ayez.",
            "Over-formal MSA in casual chat.",
            "Jokes about religion or family honour.",
            "Assuming Najdi features fit every Saudi (Hijazi uses eish, not wesh).",
        ),
        examples=(
            Example("Hi, how are you?", "هلا والله! وش لونك؟", "Warm Najdi greeting.", "Hala wallah! Wesh lonak?"),
            Example("I'm so sorry for your loss.", "عظّم الله أجركم وأحسن عزاكم وغفر لميتكم.", "The standard condolence formula.", "3aẓẓam Allah ajrakum w a7san 3azakum w ghafar li mayyitkum."),
            Example("Could you send me the report today?", "لو تكرمت، ترسل لي التقرير اليوم؟", "Law tikarramt is polite without being stiff.", "Law tikarramt, tirsil li et-taqrir el-yom?"),
        ),
        resource_level="higher",
        weak_spots="Saudi Arabic is varied (Najdi, Hijazi, southern, eastern). Only urban Najdi with some Hijazi is targeted; the model may blend in general Gulf (Emirati/Kuwaiti) words. Latin-letter Saudi texting is less common, so spelling is less settled.",
        latin_conventions=ARABIZI + " Saudis use 3 for ع, 7 for ح; Najdi often pronounces ق as g and ك as ts/ch in some words.",
    ),
    # ------------------------------------------------------------------ Levant
    LanguageProfile(
        code="apc",
        name="Levantine Arabic",
        native_name="اللهجة الشامية",
        region="Levant",
        bcp47="apc",
        scripts=(ARABIC, LATIN),
        default_script=ARABIC,
        voice=(
            "Urban Levantine (Damascus/Beirut/Amman/Jerusalem common ground): soft, affectionate, generous with "
            "compliments and blessings. Lebanese speakers mix in French and English freely."
        ),
        greetings=(
            "Marḥaba (مرحبا) - reply: Marḥabtein / Ahlein",
            "Kifak? (to a man) / Kifik? (to a woman) (كيفك؟)",
            "Shu akhbarak? (شو أخبارك؟)",
            "Sabaḥ el-kheir (صباح الخير) - reply: Sabaḥ el-noor / Sabaḥ el-ward",
        ),
        politeness=(
            "'Law sama7t' / 'iza bitrid' (if you please) and 'mn fadlak' are please; 'Merci' or 'Yislamo' thanks.",
            "Elders: ya 3ammo (uncle), ya khalto (aunt), 7adertak for formal 'you'.",
            "'Tekram' or 'tekram 3aynak' (تكرم عينك) means 'with pleasure', agreeing warmly to a request.",
            "Affectionate address is normal: ya 3ayni, ya albi, habibi/habibti, even with acquaintances.",
        ),
        idioms=(
            Idiom("Yislamo idek / idaiki", "Bless your hands", "Thanking someone for food or work they made."),
            Idiom("Sa7tein", "Bon appétit / to your health", "When someone eats or gets something new."),
            Idiom("Allah yer7amo", "May God have mercy on him", "Condolences."),
            Idiom("Ma fi mushkle", "No problem", "Reassurance."),
        ),
        avoid=(
            "Egyptian forms: ezzayak, 3ayez, eh, keda.",
            "Gulf or Moroccan words: wesh, abi, bzaf, kidayr.",
            "MSA in casual speech.",
            "Mixing country markers carelessly (Lebanese 'kifak' vs Jordanian 'kif 7alak'); default to common Levantine.",
        ),
        examples=(
            Example("Hi, how are you?", "مرحبا، كيفك؟ شو أخبارك؟", "Common pan-Levantine greeting.", "Marḥaba, kifak? Shu akhbarak?"),
            Example("Thank you for the food, it was delicious!", "يسلمو إيديكي، كان كتير زاكي!", "Blesses the cook's hands (to a woman) instead of a literal thank you.", "Yislamo idaiki, kan ktir zaki!"),
            Example("Could you send me the report today?", "لو سمحت، فيك تبعتلي التقرير اليوم؟", "Fik = can you, a Levantine marker.", "Law sama7t, fik teb3atli el-taqrir el-yom?"),
        ),
        resource_level="higher",
        weak_spots="'Levantine' covers four countries; output aims for common ground and may sound slightly 'off' to a Lebanese or Palestinian ear. Choosing between Lebanese French code-mixing and Jordanian/Syrian norms is not configurable.",
        latin_conventions=ARABIZI + " Levantine speakers use 2 for the glottal stop, 3 for ع, 7 for ح.",
    ),
    # ------------------------------------------------------------------ East Africa
    LanguageProfile(
        code="sw",
        name="Swahili",
        native_name="Kiswahili",
        region="East Africa",
        bcp47="sw",
        scripts=(LATIN,),
        default_script=LATIN,
        voice=(
            "Standard Swahili understood in Tanzania and Kenya. Greetings are long and respectful; age-based "
            "respect is built in (Shikamoo to elders). Kenyan urban youth speech (Sheng) is not targeted."
        ),
        greetings=(
            "Habari? / Habari za asubuhi? (how are you? / good morning) - reply: Nzuri",
            "Hujambo? - reply: Sijambo",
            "Shikamoo (to an elder) - reply: Marahaba",
            "Mambo? - reply: Poa (casual, young people)",
        ),
        politeness=(
            "'Tafadhali' is please; 'Asante (sana)' thank you; 'Samahani' excuse me / sorry.",
            "'Pole' expresses sympathy (for illness, tiredness, loss), not an apology for your own fault.",
            "Elders: Mzee (older man), Mama/Bibi (older woman); colleagues: Bwana / Bi.",
        ),
        idioms=(
            Idiom("Pole sana kwa msiba", "Deep sympathy for the bereavement", "Condolences."),
            Idiom("Haraka haraka haina baraka", "Haste has no blessing", "Encouraging patience."),
            Idiom("Polepole ndio mwendo", "Slowly is the way", "Encouragement to go steady."),
            Idiom("Karibu", "Welcome / you're welcome", "Hospitality and reply to thanks."),
        ),
        avoid=(
            "Tourist clichés like 'Hakuna matata' and 'Jambo' in real messages.",
            "Confusing pole (sympathy) and samahani (apology).",
            "Wrong noun-class agreement (prefix mismatches are a classic machine-translation tell).",
        ),
        examples=(
            Example("Good morning, how are you? (to an elder)", "Shikamoo. Habari za asubuhi?", "Elder greeting first."),
            Example("I'm so sorry for your loss.", "Pole sana kwa msiba.", "Pole, not samahani."),
            Example("Could you send me the report today, please?", "Tafadhali, unaweza kunitumia ripoti leo?", "Natural modern business wording."),
        ),
        resource_level="higher",
        weak_spots="Better covered than the Nigerian languages, but Kenyan and Tanzanian preferences differ and the output may mix them. Noun-class agreement errors can still appear.",
    ),
    # ------------------------------------------------------------------ Europe
    LanguageProfile(
        code="fr",
        name="French",
        native_name="Français",
        region="Europe",
        bcp47="fr",
        scripts=(LATIN,),
        default_script=LATIN,
        voice=(
            "Metropolitan French by default. Natural French is less effusive than English: fewer exclamation "
            "marks, fewer 'amazing's, and clear tu/vous choices."
        ),
        greetings=(
            "Bonjour (default, any time until evening) / Bonsoir",
            "Salut / Coucou (casual, friends and family)",
            "Ça va ? - reply: Ça va, et toi ? / Très bien, merci, et vous ?",
        ),
        politeness=(
            "Tu for friends, family, children and peers who invite it; vous for strangers, clients, elders, a boss, and any group.",
            "Formal requests: 'Pourriez-vous...', 'Je vous serais reconnaissant(e) de...'; emails close with 'Bien cordialement' or 'Cordialement'.",
            "Always say 'Bonjour' before a request, even in shops and short messages.",
            "French typography in France puts a space before ? ! : ;",
        ),
        idioms=(
            Idiom("Pas de souci", "No worries", "Casual reassurance."),
            Idiom("Ça marche", "Sounds good / deal", "Agreeing casually."),
            Idiom("Je croise les doigts pour toi", "Fingers crossed for you", "Wishing luck."),
            Idiom("Toutes mes condoléances", "My deepest condolences", "Condolences."),
        ),
        avoid=(
            "False friends: actuellement (= currently), éventuellement (= possibly), librairie (= bookshop), excité (has a sexual connotation in some contexts), 'demander' (= ask, not demand).",
            "Anglicisms and calques such as 'faire du sens' (use 'avoir du sens') or 'avoir du fun'.",
            "Overly enthusiastic English register ('C'est incroyable !!!').",
            "Using tu with someone who should get vous.",
        ),
        examples=(
            Example("Hey, how's it going?", "Salut, ça va ?", "Short and casual; space before ? per French typography."),
            Example("I'm so sorry for your loss.", "Toutes mes condoléances. Je pense fort à vous.", "Fixed formula plus a personal line."),
            Example("Could you send me the report today?", "Bonjour, pourriez-vous m'envoyer le rapport aujourd'hui, s'il vous plaît ?", "Bonjour first, vous, conditional."),
        ),
        resource_level="higher",
        weak_spots="Strong overall. West African, Belgian, Swiss and Canadian French differ in vocabulary and are not separate options yet.",
    ),
)

PROFILES: dict[str, LanguageProfile] = {p.code: p for p in _PROFILES}


def get_profile(code: str) -> LanguageProfile | None:
    return PROFILES.get(code)


def grouped_public() -> list[dict]:
    """Languages grouped by region in display order, for the picker."""
    groups = []
    for region in REGION_ORDER:
        items = [p.public() for p in _PROFILES if p.region == region]
        if items:
            groups.append({"region": region, "languages": items})
    return groups
