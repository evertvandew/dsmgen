Feature: Generate Rust code for Arduino

    Scenario Outline: block construction
        Given the Blinky network
        When generating the main program
        Then the number of blocks to be instantiated equals 4
            And the generated instantiation for block <block> equals <code>

            Examples:
                | block | code                          |
                |   0   | "lib::arduino_uno::new()"     |
                |   1   | "lib::toggle::new()"          |
                |   2   | "lib::DO::new::<P0>(p0, 1)"   |
                |   3   | "lib::counter::new(100)"      |

    Scenario Outline: Connection construction
        Given the Blinky network
        When generating the main program
        Then the number of connections to be instantiated equals 3
        And the constructor for connection <conn> equals <code>

        Examples:
            | conn | code                          |
            |  0   | "Connection((1, 0),(2, 0))"   |
            |  1   | "Connection((0, 0),(3, 0))"   |
            |  2   | "Connection((3, 0),(1, 0))"   |

    @active
    Scenario Outline:
        Given the Blinky network
        When generating the main program
        Then the declaration for block <block> equals <code>
        Examples:
            | block | code               |
            |   0   | "lib::arduino_uno" |
            |   1   | "lib::toggle"      |
            |   2   | "lib::DO<P0>"      |
            |   3   | "lib::counter"     |

    @active
    Scenario: determining program details
        Given the Blinky network
        When generating the main program
        Then there is 1 parameters
        And the type of parameter 0 is OutputPin
        And the program parameter string is "<P0: OutputPin>"
        And the recipient of parameter 0 is block 2
        And the program name is TheProgram
        And the program instantiation parameters equals "pins.d13.into_output()"

