from app.utils import helper


class Audio(helper.Helper):
    mode = helper.HelperMode.snake_case
    VOCALS = helper.Item()
    VOICE = helper.Item()
    DRUM = helper.Item()
    BASS = helper.Item()
    ELECTRIC_GUITAR = helper.Item()
    ACOUSTIC_GUITAR = helper.Item()
    PIANO = helper.Item()
    SYNTHESIZER = helper.Item()
    STRINGS = helper.Item()
    WIND = helper.Item()
    LEVEL_LOW = 0
    LEVEL_MID = 1
    LEVEL_HIGH = 2

    def __init__(self):
        self.stem = None
        self.no_stem = None

    def __repr__(self):
        return f'{self.stem=}\n{self.no_stem=}'

    def __bool__(self):
        return bool(self.stem and self.no_stem)
