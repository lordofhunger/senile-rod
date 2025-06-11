open Stdlib

(* --- Text Processing Helpers --- *)

let tokenize_line line =
  String.split_on_char ' ' line
  |> List.filter (fun word -> String.trim word <> "")

let capitalize_string_first_char s =
  if s = "" then s
  else
    let first_char = Char.uppercase_ascii s.[0] in
    let rest_of_string = String.sub s 1 (String.length s - 1) in
    String.make 1 first_char ^ rest_of_string

let replace_placeholder_with_space s =
  let buffer = Buffer.create (String.length s) in
  String.iter (fun c ->
    if c = '\x1F' then Buffer.add_char buffer ' '
    else Buffer.add_char buffer c
  ) s;
  Buffer.contents buffer

(* --- List Helpers --- *)

let list_slice (lst: 'a list) (start_index: int) (length: int) : 'a list =
  let rec aux current_index acc = function
    | [] -> List.rev acc
    | h :: t ->
      if current_index >= start_index && current_index < start_index + length then
        aux (current_index + 1) (h :: acc) t
      else if current_index >= start_index + length then
        List.rev acc
      else
        aux (current_index + 1) acc t
  in
  aux 0 [] lst

(* --- Markov Chain Core Logic --- *)

type chain_key = string list
type transition_table = (chain_key, string list) Hashtbl.t

let create_markov_table (order: int) (messages: string list list) : transition_table =
  let table = Hashtbl.create 100_000 in

  let add_transition key next_word =
    Hashtbl.add table key (next_word :: (Hashtbl.find_opt table key |> Option.value ~default:[]))
  in

  let start_padding = List.init order (fun _ -> "<START>") in
  let end_marker = "<END>" in

  List.iter (fun tokens ->
    let padded_tokens = start_padding @ tokens @ [end_marker] in
    for i = 0 to List.length padded_tokens - order - 1 do
      let key = list_slice padded_tokens i order in
      let next_word = List.nth padded_tokens (i + order) in
      add_transition key next_word
    done
  ) messages;
  table

let generate_sequence (table: transition_table) (order: int) (max_length: int) : string list =
  let rec generate_aux current_state accumulated_words count =
    if count >= max_length then accumulated_words
    else
      match Hashtbl.find_opt table current_state with
      | None | Some [] -> accumulated_words
      | Some options ->
          let next_word = List.nth options (Random.int (List.length options)) in
          if next_word = "<END>" then accumulated_words
          else
            let new_state = List.tl (current_state @ [next_word]) in
            generate_aux new_state (accumulated_words @ [next_word]) (count + 1)
  in
  let initial_state = List.init order (fun _ -> "<START>") in
  generate_aux initial_state [] 0

(* --- Message Filtering --- *)

let problematic_end_words = [
  "and"; "but"; "or"; "if"; "because"; "so"; "that"; "as"; "then"; "while";
  "though"; "although"; "unless"; "until"; "maybe"; "as well"; "still";
  "of"; "with"; "to"; "for"; "in"; "on"; "at"; "from"; "by"; "about"; "into";
  "over"; "after"; "before"; "around"; "like"; "through"; "without";
  "is"; "are"; "was"; "were"; "be"; "being"; "been";
  "this"; "these"; "those"; "the"; "a"; "an"
]

let is_bad_ending (words: string list) : bool =
  match List.rev words with
  | [] -> true
  | last_word :: _ ->
      let last_word_lower = String.lowercase_ascii last_word in
      List.exists (fun bad_word -> bad_word = last_word_lower) problematic_end_words

(* --- Main Generation Process --- *)

let read_lines_from_file (filename: string) : string list =
  let input_channel = open_in filename in
  let rec read_acc acc =
    try read_acc (input_line input_channel :: acc)
    with End_of_file -> close_in input_channel; List.rev acc
  in
  read_acc []

let () =
  Random.self_init (); (* Initialize random number generator once *)

  let all_raw_messages = read_lines_from_file "text-files/all_messages_processed.txt" in
  let processed_messages = List.map tokenize_line all_raw_messages in

  let table_order_2 = create_markov_table 2 processed_messages in
  let table_order_3 = create_markov_table 3 processed_messages in

  let rec attempt_generation (tries: int) : string list =
    if tries >= 1000 then [] (* Give up after too many tries *)
    else
      let pick_order = if Random.bool () then 2 else 3 in
      let current_table = if pick_order = 2 then table_order_2 else table_order_3 in

      let generated_words = generate_sequence current_table pick_order 15 in

      if generated_words = [] || is_bad_ending generated_words then
        attempt_generation (tries + 1) (* Retry if empty or bad ending *)
      else
        generated_words
  in

  let final_words = attempt_generation 0 in

  let final_sentence =
    final_words
    |> String.concat " "
    |> capitalize_string_first_char
    |> replace_placeholder_with_space
  in

  print_endline final_sentence
