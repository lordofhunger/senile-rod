#!/bin/bash

eval $(opam env)
dune build
python3 bot.py
