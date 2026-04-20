import os
import re

REPO_ROOT = '/home/saboor/code/hadith-api-toon'

intros = {
    'bayhaqi': {
        'en': 'As-Sunan al-Kubra by Imam al-Bayhaqi (d. 458 AH) is one of the most comprehensive and scholarly collections of Hadith. Organized according to the chapters of Shafi\'i jurisprudence, it contains over 20,000 narrations. It is renowned for its critical analysis of chains and its preservation of legal proofs.',
        'ur': 'امام بیہقی (وفات 458ھ) کی السنن الکبریٰ حدیث کے سب سے مستند اور جامع مجموعوں میں سے ایک ہے۔ یہ کتاب شافعی فقہ کے ابواب پر ترتیب دی گئی ہے اور اس میں 20,000 سے زائد احادیث شامل ہیں۔ یہ کتاب اپنی اسناد کی تحقیق اور فقہی دلائل کی فراہمی کے لیے علمی حلقوں میں انتہائی معروف ہے۔',
        'ar': 'السنن الكبرى للإمام البيهقي (ت ٤٥٨ هـ) هو أحد أجل كتب الحديث النبوي وأوسعها. رتبه المؤلف على أبواب الفقه الشافعي، ويحتوي على أكثر من عشرين ألف حديث وأثر. يتميز الكتاب بدقة الاستنباط الفقهي ونقد الأسانيد.'
    },
    'mishkat': {
        'en': 'Mishkat al-Masabih by Wali al-Din al-Tabrizi (d. 741 AH) is an expanded version of al-Baghawi\'s Masabih al-Sunnah. It categorizes hadiths into sections based on their source (Bukhari/Muslim, others, and unique additions), making it an essential textbook for students of Hadith worldwide.',
        'ur': 'مشکاۃ المصابیح ولی الدین التبریزی (وفات 741ھ) کی تالیف ہے، جو امام بغوی کی \'مصابیح السنہ\' کی توسیع شدہ شکل ہے۔ اس میں احادیث کو ان کے مصادر (بخاری و مسلم، دیگر کتب ستہ، اور اضافی روایات) کے لحاظ سے تقسیم کیا گیا ہے، جس کی وجہ سے یہ طلبہِ حدیث کے لیے ایک بنیادی نصابی کتاب کی حیثیت رکھتی ہے۔',
        'ar': 'مشكاة المصابيح لولي الدين التبريزي (ت ٧٤١ هـ) هو تهذيب وتكملة لكتاب \'مصابيح السنة\' للبغوي. رتب فيه الأحاديث ضمن فصول فقهية وقسمها إلى فئات حسب مصدرها، مما جعل الكتاب مرجعاً تعليمياً أساسياً لطلاب الحديث.',
        'hi': 'मिश्कात अल-मसाबीह वली अल-दीन अल-तबरीज़ी (मृत्यु 741 हिजरी) द्वारा अल-बग़वी की \'मसाबीह अल-सुन्नत\' का विस्तृत संस्करण है। यह हदीसों को उनके स्रोतों के आधार पर वर्गीकृत करता है, जिससे यह हदीस के छात्रों के लिए एक महत्वपूर्ण पाठ्यपुस्तक बन गई है।'
    },
    'muajam-tabarani-saghir': {
        'en': 'Al-Mu\'jam al-Saghir is part of Imam al-Tabarani\'s (d. 360 AH) famous trilogy of dictionaries. This smaller collection is unique as it contains one or two narrations from each of the author\'s 1,000+ teachers, reflecting the vast network of transmission in the 4th century AH.',
        'ur': 'المعجم الصغیر امام طبرانی (وفات 360ھ) کی مشہور معاجم ثلاثہ کا حصہ ہے۔ یہ مختصر مجموعہ اس لحاظ سے منفرد ہے کہ اس میں مصنف نے اپنے ایک ہزار سے زائد اساتذہ میں سے ہر ایک سے ایک یا دو احادیث روایت کی ہیں۔',
        'ar': 'المعجم الصغير للإمام الطبراني (ت ٣٦٠ هـ) هو أحد معاجمه الثلاثة الشهيرة. يقتصر فيه المؤلف على رواية حديث أو حديثين عن كل شيخ من شيوخه الذين زادوا على الألف، مما يظهر سعة مروياته ورحلاته العلمية.'
    },
    'musannaf-ibn-abi-shaybah': {
        'en': 'The Musannaf of Ibn Abi Shaybah (d. 235 AH) is one of the earliest and largest primary sources of Hadith and legal opinions. It is exceptional for preserving not only the Prophet\'s sayings but also the legal rulings (fatwas) of the Companions and the Successors (Tabi\'un).',
        'ur': 'مصنف ابن ابی شیبہ (وفات 235ھ) حدیث اور فقہی آراء کا قدیم ترین اور سب سے بڑا ذخیرہ ہے۔ اس کتاب کی خاص بات یہ ہے کہ اس میں نہ صرف احادیثِ نبوی بلکہ صحابہ کرام اور تابعین کے فتاویٰ اور فقہی اقوال کو بھی بڑی تفصیل سے جمع کیا گیا ہے۔',
        'ar': 'مصنف ابن أبي شيبة (ت ٢٣٥ هـ) من أقدم وأكبر مصادر الحديث النبوي والآثار. يتميز بجمعه لأقوال الصحابة والتابعين وفتاواهم إلى جانب الأحاديث المرفوعة، مما يجعله مرجعاً أساسياً في الفقه المقارن.'
    },
    'musnad-ahmed': {
        'en': 'The Musnad of Imam Ahmad ibn Hanbal (d. 241 AH) is one of the most authoritative and voluminous works in Hadith history. It contains over 27,000 hadiths organized by the primary narrator (Sahabi), serving as a foundational pillar of the Hanbali school and the wider Sunni tradition.',
        'ur': 'مسند احمد بن حنبل (وفات 241ھ) تاریخِ حدیث کے مستند ترین اور ضخیم ترین مجموعوں میں سے ایک ہے۔ اس میں 27,000 سے زائد احادیث کو راویِ اول (یعنی صحابی) کی ترتیب سے جمع کیا گیا ہے، اور یہ حنبلی فقہ اور عمومی اہل سنت کے نزدیک ایک بنیادی ستون ہے۔',
        'ar': 'مسند الإمام أحمد بن حنبل (ت ٢٤١ هـ) هو واحد من أعظم دواوين السنة وأكثرها شمولاً. يضم أكثر من سبعة وعشرين ألف حديث مرتبة على مسانيد الصحابة، ويعد أصلاً من أصول المذهب الحنبلي والسنة النبوية قاطبة.'
    },
    'mustadrak': {
        'en': 'Al-Mustadrak \'ala al-Sahihayn by Al-Hakim al-Nishapuri (d. 405 AH) was compiled to supplement the works of Bukhari and Muslim. It contains hadiths that the author believed met the criteria of the two Sahihs but were not included in them.',
        'ur': 'المستدرک علی الصحیحین امام حاکم نیشاپوری (وفات 405ھ) کی تالیف ہے، جس کا مقصد بخاری و مسلم کی کتب کی تکمیل کرنا تھا۔ اس میں وہ احادیث جمع کی گئی ہیں جن کے بارے میں مصنف کا خیال تھا کہ وہ بخاری و مسلم کی شرائط پر پوری اترتی ہیں لیکن ان کتب میں شامل نہیں ہو سکیں۔',
        'ar': 'المستدرك على الصحيحين للحاكم النيسابوري (ت ٤٠٥ هـ) استدرك فيه الأحاديث التي يراها على شرط البخاري ومسلم أو أحدهما ولم يخرجاها في كتابيهما، مع تبيين درجة صحة ما لم يكن على شرطهما.'
    },
    'sahih-ibn-khuzaymah': {
        'en': 'Sahih Ibn Khuzaymah (d. 311 AH) is a highly esteemed collection of authentic hadiths. The author adhered to rigorous conditions of narrators\' reliability and continuity, making it a primary source for authentic narrations outside the two Sahihs.',
        'ur': 'صحیح ابن خزیمہ (وفات 311ھ) صحیح احادیث کا ایک معتبر مجموعہ ہے۔ مصنف نے اس میں روات کی ثقاہت اور سند کے اتصال کے لیے انتہائی سخت شرائط رکھی تھیں، جس کی وجہ سے بخاری و مسلم کے بعد اسے صحیح احادیث کا اہم ماخذ مانا جاتا ہے۔',
        'ar': 'صحيح ابن خزيمة (ت ٣١١ هـ) هو أحد كتب الحديث التي التزمت بالصحة. اشترط فيه مؤلفه \'إمام الأئمة\' شروطاً دقيقة في العدالة والاتصال، وهو مرتب على الأبواب الفقهية.'
    },
    'silsila-sahih': {
        'en': 'Silsilat al-Ahadith as-Sahihah is a modern critical effort by Sheikh Muhammad Nasir al-Din al-Albani (d. 1419 AH). It compiles authentic narrations from various classical sources, providing detailed referencing (takhrij) and evaluation to distinguish authentic Sunnah from weak reports.',
        'ur': 'سلسلہ الاحادیث الصحيحہ شیخ محمد ناصر الدین البانی (وفات 1419ھ) کی ایک جدید علمی کاوش ہے۔ اس میں مختلف کلاسیکی مصادر سے صحیح احادیث کو جمع کیا گیا ہے اور ان کی تفصیلی تحقیق اور تخریج پیش کی گئی ہے تاکہ ضعیف روایات کے مقابلے میں صحیح سنت کو نمایاں کیا جا سکے۔',
        'ar': 'سلسلة الأحاديث الصحيحة للشيخ محمد ناصر الدين الألباني (ت ١٤١٩ هـ) هي مشروع حديثي معاصر يهدف إلى تنقية السنة من الأحاديث الضعيفة وجمع ما ثبت منها، مع التخريج المفصل والتعليق العلمي على فوائد الأحاديث.'
    },
    'sunan-darmi': {
        'en': 'The Sunan (or Musnad) of Imam al-Darimi (d. 255 AH) is a significant hadith collection known for its unique structure and high-quality chains. It starts with an introductory section on the virtues of the Prophet and knowledge, followed by legal topics. It is revered for its reliability.',
        'ur': 'سنن الدارمی (یا مسند الدارمی) امام عبداللہ بن عبدالرحمن الدارمی (وفات 255ھ) کا مجموعہ ہے، جو اپنی منفرد ترتیب اور اعلیٰ اسناد کے لیے معروف ہے۔ یہ کتاب فضائلِ علم اور سیرتِ نبوی کے تعارف سے شروع ہوتی ہے اور اسے علمی حلقوں میں انتہائی ثقہ مانا جاتا ہے۔',
        'ar': 'سنن الدارمي (ت ٢٠٥ هـ) من كتب الحديث المعتمدة والمشهورة بجودة أسانيدها. افتتحه المؤلف بمقدمة حافلة في فضل العلم واتباع السنة وسيرة الرسول ﷺ، ثم رتبه على الأبواب الفقهية.'
    }
}

for book_id, data in intros.items():
    info_path = f"{REPO_ROOT}/editions/{book_id}/info.toon"
    if not os.path.exists(info_path):
        print(f"Skipping {book_id}, path not found")
        continue
    
    with open(info_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Replace default intro or update it
    # Format: intro: \"...\"
    if 'intro: \"...\"' in content or 'intro: \"\"' in content:
        content = content.replace('intro: \"...\"', f'intro: \"{data["en"]}\"')
        content = content.replace('intro: \"\"', f'intro: \"{data["en"]}\"')
    else:
        # Generic replacement for intro: \"ANYTHING\"
        content = re.sub(r'intro:\s*\"[^\"]*\"', f'intro: \"{data["en"]}\"', content)
    
    # Check for existing translations and insert new ones
    # We want to place them after the intro field
    new_fields = []
    if f'intro_ur:' not in content:
        new_fields.append(f'  intro_ur: \"{data["ur"]}\"')
    if f'intro_ar:' not in content:
        new_fields.append(f'  intro_ar: \"{data["ar"]}\"')
    if 'hi' in data and f'intro_hi:' not in content:
        new_fields.append(f'  intro_hi: \"{data["hi"]}\"')
    
    if new_fields:
        # Find the line with 'intro:' and append after it
        content = re.sub(r'(intro:\s*\"[^\"]*\")', r'\1\n' + "\n".join(new_fields), content)
    
    with open(info_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Updated {book_id}")
