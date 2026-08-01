#!/usr/bin/env python3
"""
Fix fath-al-rabbani EN HN142 and HN152: both ended with the literal
pipeline-failure debug string "[corrupt: repetition loop truncated]" left
in production data. Confirmed isolated to EN only (checked all 11 other
languages - 0 matches).

HN142: full retranslation from AR/UR (existing pre-truncation EN text
diverged structurally from the source, not just cut off).
HN152: full retranslation of the believer-clause (existing pre-truncation
EN text had "believes in the testimony of the oneness of Allah" - a
mistranslation, AR/UR actually say "one whom the believers trust with
their lives and their wealth" - not just a truncation, an actual content
error that predates the truncation point).

Own translations (not LLM), written by re-reading the AR source directly.
See KNOWN_ISSUES.md fath-al-rabbani item 5 (bundled in) for full detail.
"""
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from toon_io import read_toon, write_toon, serialize_row

PATH = '/home/saboor/code/hadith-api-toon/editions/fath-al-rabbani/translations/en/sections/2.toon'

TRANSLATIONS = {
    '142': (
        "Abd al-Rahman ibn Jubayr ibn Nufayr said, on the authority of his father: We sat with "
        "al-Miqdad ibn al-Aswad (may Allah be pleased with him) one day, when a man passed by and "
        "said, \"Blessed are these two eyes that saw the Messenger of Allah (peace be upon him and "
        "his family)! By Allah, we wish we had seen what you saw and witnessed what you witnessed.\" "
        "At this al-Miqdad became angry, and I was astonished, for the man had said nothing but good. "
        "Then he turned to the man and said: \"What leads a man to wish for a scene that Allah kept "
        "him away from, when he does not know how he would have fared had he been present in it? By "
        "Allah, there were people present with the Messenger of Allah (peace be upon him and his "
        "family) whom Allah cast down on their faces into Hell, for they did not answer him or believe "
        "him. Do you not thank Allah that when He brought you forth, you knew none but your Lord, "
        "believing in what your Prophet brought, and you were spared the trial that befell others? By "
        "Allah, Allah sent the Prophet (peace be upon him and his family) at the harshest of times at "
        "which a prophet had ever been sent among the prophets, a time of spiritual dearth and "
        "ignorance, when people believed no religion was better than the worship of idols. Then he "
        "came with a criterion (Furqan) by which he distinguished between truth and falsehood, and "
        "separated a father from his son, such that a man might see his father, his son, and his "
        "brother as disbelievers, while Allah had opened the lock of his own heart to faith; he knew "
        "that if he died in disbelief, that man would enter the Fire, and his eye would never find "
        "rest, knowing his beloved was in the Fire. That is what Allah, Mighty and Majestic, referred "
        "to when He said: 'Those who say: Our Lord, grant us from among our spouses and offspring "
        "comfort to our eyes' [Surah al-Furqan: 74].\""
    ),
    '152': (
        "Musa ibn Ali said: I heard my father say, I heard Abdullah ibn Amr ibn al-'As say, I heard "
        "the Messenger of Allah (peace be upon him and his family) say: \"Do you know who the Muslim "
        "is?\" They said, \"Allah and His Messenger know best.\" He said, \"The Muslim is he from whose "
        "tongue and hand other Muslims are safe.\" He said, \"Do you know who the believer is?\" They "
        "said, \"Allah and His Messenger know best.\" He said, \"The believer is he whom the believers "
        "trust with their lives and their wealth, and the emigrant (Muhajir) is one who abandons evil "
        "and avoids it.\""
    ),
}


def main():
    d = read_toon(PATH)
    new_spans = []
    changed = 0
    for raw, fields in d['spans']:
        hn = fields[0].strip('"')
        if hn in TRANSLATIONS:
            new_fields = [hn, TRANSLATIONS[hn]]
            new_spans.append((serialize_row(new_fields), new_fields))
            changed += 1
        else:
            new_spans.append((raw, fields))

    assert changed == 2, f'expected 2 rows changed, got {changed}'
    write_toon(PATH, d['header_line'], d['block_name'], d['columns'], new_spans)
    print(f'changed: {changed} rows, new row count = {len(new_spans)}')


if __name__ == '__main__':
    main()
