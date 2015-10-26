commands = [
    (r"h(?:elp)?", "help", "{cmd_start}h(elp) - show help"),
    (r"rand(?:om)?(?: (?P<randcount>[0-9]{1,5}))?", "random_num", "{cmd_start}rand(om) max - show random number from 1"
                                                                  " to max (default 100)"),
    (r"\$(?P<currency>(?: [a-z]{3})+)?", "exchangerates", "{cmd_start}$ USD|EUR - show exchange rates"),
    (r"w(?:a|alpha) (?P<clear>forgot )?(?P<question>[ a-z0-9\+\?\^\-\*,\.\"\'=:;\(\)/%]{1,255})", "wolframalpha",
     "{cmd_start}w(alpha) - question (1-255 symbols)"),
    (r"uid (?P<server_name>.+)", "usersid", ""),
    (r"restart", "restart", ""),
    (r"update", "update", ""),
    (r"uptime", "uptime", ""),
]

