commands = [
    (r"h(?:elp)?", "help", "{cmd_start}h(elp) - show help"),
    (r"\$(?P<currency>(?: [a-z]{3})+)?", "exchangerates", "{cmd_start}$ USD|EUR - show exchange rates"),
    (r"w(?:alpha)? (?P<question>[ a-z0-9]{1,255})", "wolframalpha", "{cmd_start}w(alpha) - question (1-255 symbols)"),
]
