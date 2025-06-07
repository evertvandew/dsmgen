Feature: Generate Rust code for Arduino

    @active
    Scenario: Generating the blinky network
        Given the Blinky network
        Then the program name is "blinky"
        And the generated preamble equals
            """
            #![no_std]
            #![no_main]

            mod block_library;
            mod block_base;
            mod vecdeque;

            use embedded_hal::digital::{OutputPin};
            use block_library as lib;
            use crate::block_base::{clock_tick, Connection, Program, IoProcess};

            use panic_halt as _;
            """

    @active
    Scenario Outline: block construction
        Given the Blinky network
        When generating the main program
        Then the number of blocks to be instantiated equals 4
            And the generated instantiation for block <block> equals <code>

            Examples:
                | block | code                          |
                |   0   | "lib::arduino_uno::new()"     |
                |   1   | "lib::toggle::new()"          |
                |   2   | "lib::DO::new::<P0>(p0, 1)"  |
                |   3   | "lib::counter::new(100)"      |

    Scenario Outline: Connection construction
        Given the Blinky network
        When generating the main program
        Then the number of connections to be instantiated equals 3
        And the generated connection <conn> equals <code>

        Examples:
            | conn | code
            |  0   | "Connection((1, 0),(2, 0))"
            |  1   | "Connection((0, 0),(1, 0))"
            |  2   | "Connection((2, 0),(3, 0))"

    Scenario: program generation
        When the block declaration equals "[1, 2, 3, 4]"
        And there are 3 connections
        And the Parameters equal "[('OP', 'OutputPin')]"
        Then the generated main program declaration equals
            """
            struct TheProgram<OP: OutputPin> {
                block0: 1,
                block1: 2,
                block2: 3,
                block3: 4,
                connections: [Connection; 3],
            }
            """

    @active
    Scenario: determining program parameters
        Given the Blinky network
        When generating the main program
        Then there is 1 parameters
        And the type of parameter 0 is OutputPin
        And the recipient of parameter 0 is block 2
