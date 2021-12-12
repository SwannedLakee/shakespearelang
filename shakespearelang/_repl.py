from .shakespeare import Shakespeare
from .errors import ShakespeareError
from tatsu.exceptions import FailedParse

import readline
import sys


def _print_character(character_name, interpreter):
    character = interpreter.state.character_by_name(character_name)
    print(character)


def _run_sentences(sentences, speaking_character, opposite_character, interpreter):
    for sentence in sentences:
        if sentence.parseinfo.rule == "goto":
            print("Control flow isn't allowed in REPL.")
            # Stop this entire line of sentences
            return

        interpreter.run_sentence(sentence, speaking_character)


DEFAULT_PLAY_TEMPLATE = """
A REPL-tastic Adventure.

<dramatis personae>

                    Act I: All the World.
                    Scene I: A Stage.

[Enter <entrance list>]
"""


def start_console(characters=["Romeo", "Juliet"]):
    dramatis_personae = "\n".join([name + ", a player." for name in characters])
    entrance_list = _entrance_list_from_characters(characters)
    play = DEFAULT_PLAY_TEMPLATE.replace(
        "<dramatis personae>", dramatis_personae
    ).replace("<entrance list>", entrance_list)

    print(play)
    interpreter = Shakespeare(play)
    # Run the entrance
    interpreter.step_forward()
    run_repl(interpreter)


# E.g. ["Mercutio", "Romeo", "Tybalt"] => "Mercutio, Romeo and Tybalt"
def _entrance_list_from_characters(characters):
    all_commas = ", ".join(characters)
    split_on_last = all_commas.rsplit(", ", 1)
    return " and ".join(split_on_last)


def debug_play(text, input_style="interactive", output_style="verbose"):
    interpreter = Shakespeare(text, input_style=input_style, output_style=output_style)

    def on_breakpoint():
        print("-----\n", interpreter.next_event_text(), "\n-----\n")
        run_repl(interpreter)

    interpreter.run(on_breakpoint)


def run_repl(interpreter):
    previous_input_style = interpreter.get_input_style()
    previous_output_style = interpreter.get_output_style()
    interpreter.set_input_style("interactive")
    interpreter.set_output_style("verbose")
    current_character = None

    while True:
        try:
            repl_input = input(">> ")
            if repl_input in ["exit", "quit"]:
                sys.exit()
            elif repl_input == "continue":
                break
            elif repl_input == "next":
                if interpreter.play_over():
                    break
                interpreter.step_forward()
                if interpreter.play_over():
                    break
                print("\n-----\n", interpreter.next_event_text(), "\n-----\n")
            elif repl_input == "state":
                print(str(interpreter.state))
            else:
                # TODO: make this not an awkward return value
                current_character = _run_repl_input(
                    interpreter, repl_input, current_character
                )
        except ShakespeareError as e:
            print(str(e), file=sys.stderr)

    interpreter.set_input_style(previous_input_style)
    interpreter.set_output_style(previous_output_style)


def _run_repl_input(interpreter, repl_input, current_character):
    ast = interpreter.parse(repl_input + "\n", "repl_input")

    event = ast.event
    sentences = ast.sentences
    character = ast.character
    value = ast.value

    # Events that are lines should be considered sets of sentences.
    if event and event.parseinfo.rule == "line":
        current_character = event.character
        sentences = event.contents
        event = None

    if event:
        # Note we do not have to worry about control flow here because only lines
        # can cause that -- these have been extracted to sentences above.
        interpreter.run_event(event)
    elif sentences:
        if not current_character:
            print("Who's saying this?")
            return

        speaking_character = interpreter.state.character_by_name(current_character)
        interpreter.state.assert_character_on_stage(speaking_character)
        opposite_character = interpreter.state.character_opposite(speaking_character)

        _run_sentences(sentences, speaking_character, opposite_character, interpreter)
    elif value:
        if character:
            current_character = character

        speaking_character = interpreter.state.character_by_name(current_character)
        interpreter.state.assert_character_on_stage(speaking_character)
        result = interpreter.evaluate_expression(value, speaking_character)

        print(result)
    elif character:
        _print_character(character, interpreter)

    return current_character