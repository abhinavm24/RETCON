"""Original, deliberately short demo fiction and its explicit scene metadata."""

def seed_story():
    def p(id, text, characters, speakers, time, location, scene):
        return dict(id=id, text=text, characters=characters, speakers=speakers,
                    time=time, location=location, scene=scene)

    chapters = [
        dict(id=1, title="A room without a door", paragraphs=[
            p("1-1", "Aster had been built for twelve people and a thousand unanswered questions. By the ninth winter, only five people remained. Sera liked the silence. It made the machinery sound honest.", ["sera"], [], "21:00", "Observatory", "arrival"),
            p("1-2", "At 21:07, the observatory sealed itself. Ivo pressed his palm against the glass. Beyond it, a red warning pulsed beside an empty chair. The station's last transmission contained four words: ONE OF US LIED.", ["ivo"], [], "21:07", "Observatory", "warning"),
            p("1-3", "Sera found a brass key beneath the chair. It was warm, which was impossible. There had been nobody inside the observatory for six hours.", ["sera"], [], "21:09", "Observatory", "key"),
        ]),
        dict(id=2, title="The airlock", paragraphs=[
            p("2-1", 'Mara stood at the outer airlock with her hand over the manual release. “I changed the access logs,” Mara said. “I thought I was protecting you.” Behind her, the inner door began to close.', ["mara"], ["mara"], "21:20", "Airlock", "confession"),
            p("2-2", "Sera reached the corridor as the pressure alarm sounded. Through the small window she saw Mara turn toward the black glass. Then the emergency shutter dropped. When the airlock camera returned, the chamber was empty. No suit beacon answered.", ["sera", "mara"], [], "21:22", "Airlock", "loss"),
            p("2-3", "Ivo shut down the alarm. Neither of them said the word they were thinking. In the station ledger, Sera left one line unfinished: Mara, last seen at the outer lock.", ["ivo", "sera", "mara"], [], "21:24", "Control", "ledger"),
        ]),
        dict(id=3, title="The wrong voice", paragraphs=[
            p("3-1", "The control room smelled of hot copper. Sera spread the access logs across the desk. Every entry after 21:00 had been rewritten with the same credential: hers.", ["sera"], [], "21:30", "Control", "logs"),
            p("3-2", 'Mara leaned over the console. “The key opens the lower archive,” Mara said. “I hid the original logs there.” Ivo looked from her to the brass key on the desk.', ["mara", "ivo"], ["mara"], "21:32", "Control", "reveal"),
            p("3-3", "Sera turned the key once in her hand. If the original logs survived, someone had wanted them to be found. The question was who would reach the archive first.", ["sera"], [], "21:34", "Control", "decision"),
        ]),
        dict(id=4, title="What the archive kept", paragraphs=[
            p("4-1", "Below the station, shelves of handwritten notebooks stood in rows. The archive had no network connection. Whatever had changed the digital record could not reach this room.", [], [], "21:45", "Archive", "descent"),
            p("4-2", '“Look at the date,” Mara whispered, holding the notebook open. Sera saw tomorrow written at the top of the page. Beneath it was an exact account of the airlock alarm.', ["mara", "sera"], ["mara"], "21:47", "Archive", "notebook"),
            p("4-3", "Ivo found the missing page folded into the spine. It held a single instruction: do not trust the clock. From somewhere above them came the sound of a door unlocking.", ["ivo"], [], "21:49", "Archive", "clock"),
        ]),
        dict(id=5, title="The things that remain", paragraphs=[
            p("5-1", "Sera remembered Mara's laugh, the way it always arrived a moment before the joke. The memory hurt more in a room full of clocks. She put the brass key beside the empty chair.", ["sera", "mara"], [], "22:00", "Observatory", "memory"),
            p("5-2", '“The station clock was eleven minutes fast,” Ivo said. “The notebook did not predict anything. Someone wanted us to think it did.” Sera looked at the unfinished line in the ledger.', ["ivo", "sera"], ["ivo"], "22:02", "Observatory", "answer"),
            p("5-3", "Outside, the first supply light appeared against the dark. Sera closed the ledger without finishing the line. Some answers belonged to the person who would have to live with them.", ["sera"], [], "22:05", "Observatory", "end"),
        ]),
    ]
    for chapter in chapters:
        chapter.update(status="clean", version=1)
    return dict(id="aster", title="The Aster Protocol", subtitle="A locked-room mystery at the edge of the world",
                version=1, characters=[dict(id="mara", name="Mara", status="unresolved", death_chapter=None),
                                      dict(id="sera", name="Sera", status="alive", death_chapter=None),
                                      dict(id="ivo", name="Ivo", status="alive", death_chapter=None)], chapters=chapters)
