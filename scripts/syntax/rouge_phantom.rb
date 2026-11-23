# frozen_string_literal: true

require "rouge"

module Rouge
  module Lexers
    # Rouge lexer for Phantom dual-layer Python.
    #
    # Extends Rouge::Lexers::Python to highlight Phantom version prefixes
    # (`#: phantom:<version>`), encoding block markers (`#:ws:begin`, `#:ws:end`,
    # `#:zw:begin`, `#:zw:end`, `#:phantom:hybrid`), and instruction identifiers.
    class Phantom < Rouge::Lexers::Python
      title "Phantom"
      desc "Phantom dual-layer Python instruction layer"
      tag "phantom"
      aliases "phantom-py"

      PHANTOM_INSTRUCTIONS = %w[
        event.declare
        event.on
        diagnostic.note
        diagnostic.warn
        counter.create
        counter.increment
        counter.decrement
        counter.reset
        meta.author
        meta.version
        meta.license
        meta.tags
        meta.description
      ].freeze

      PHANTOM_INSTRUCTION_PATTERN = /\b(?:#{PHANTOM_INSTRUCTIONS.map { |i| Regexp.escape(i) }.join("|")})\b/

      prepend :root do
        rule(/#:(?:ws:begin|ws:end|zw:begin|zw:end|phantom:hybrid)\b/, Comment::Preproc)
        rule(/#:\s*phantom:/) do
          token Comment::Special
          push :phantom_instruction
        end
      end

      state :phantom_instruction do
        rule(/\d+\.\d+\.\d+/, Literal::Number)
        rule(PHANTOM_INSTRUCTION_PATTERN, Name::Builtin)
        rule(/"(?:\\.|[^"\\])*"/, Literal::String::Double)
        rule(/'(?:\\.|[^'\\])*'/, Literal::String::Single)
        rule(/-?\d+/, Literal::Number::Integer)
        rule(/[(),\[\]]/, Punctuation)
        rule(/[ \t]+/, Text::Whitespace)
        rule(/\n/, Text::Whitespace, :pop!)
        rule(/[^\s\n]+/, Comment::Special)
      end
    end
  end
end
