(define (domain mps500-domain)
 (:requirements :strips :typing :negative-preconditions)
 (:types
    carrier product locatable - object
    conveyorbelt station - locatable
    processing rawpartswarehouse assembly quality bufferstorage shipping - station
 )
 (:predicates 
             (empty ?c - carrier)
             (loaded ?c - carrier ?p - product)
             (on ?c - carrier ?cb - conveyorbelt)
             (processed ?p - product)
             (inspected ?p - product)
             (assembled ?p - product)
             (stored ?p - product)
             (shipped ?p - product)
             (available ?p - product ?ct - station)
             (occupied ?cb - conveyorbelt)
             (connected ?cb1 - locatable ?cb2 - locatable)
 )
 (:action move
  :parameters ( ?c - carrier ?cb1_0 - conveyorbelt ?cb2_0 - conveyorbelt)
  :precondition (and (not (empty ?c)) (on ?c ?cb1_0) (not (occupied ?cb2_0)) (connected ?cb1_0 ?cb2_0))
  :effect (and (not (on ?c ?cb1_0)) (on ?c ?cb2_0) (not (occupied ?cb1_0)) (occupied ?cb2_0)))
 (:action proceed
  :parameters ( ?c - carrier ?cb1_0 - conveyorbelt ?cb2_0 - conveyorbelt)
  :precondition (and (on ?c ?cb1_0) (not (occupied ?cb2_0)) (empty ?c) (connected ?cb1_0 ?cb2_0))
  :effect (and (not (on ?c ?cb1_0)) (on ?c ?cb2_0) (not (occupied ?cb1_0)) (occupied ?cb2_0)))
 (:action process
  :parameters ( ?c - carrier ?p - product ?cb - conveyorbelt ?ct_0 - processing)
  :precondition (and (loaded ?c ?p) (on ?c ?cb) (connected ?cb ?ct_0) (not (processed ?p)))
  :effect (and (processed ?p)))
 (:action load
  :parameters ( ?c - carrier ?p - product ?ct_1 - rawpartswarehouse ?cb1_0 - conveyorbelt)
  :precondition (and (available ?p ?ct_1) (empty ?c) (not (processed ?p)) (connected ?cb1_0 ?ct_1) (on ?c ?cb1_0))
  :effect (and (not (available ?p ?ct_1)) (not (empty ?c)) (loaded ?c ?p)))
 (:action assemble
  :parameters ( ?c - carrier ?p - product ?ct_2 - assembly ?cb1_0 - conveyorbelt)
  :precondition (and (loaded ?c ?p) (inspected ?p) (not (assembled ?p)) (connected ?cb1_0 ?ct_2) (on ?c ?cb1_0))
  :effect (and (assembled ?p)))
 (:action inspect
  :parameters ( ?c - carrier ?p - product ?ct_3 - quality ?cb1_0 - conveyorbelt)
  :precondition (and (loaded ?c ?p) (processed ?p) (not (inspected ?p)) (connected ?cb1_0 ?ct_3) (on ?c ?cb1_0))
  :effect (and (inspected ?p)))
 (:action store
  :parameters ( ?c - carrier ?p - product ?ct_4 - bufferstorage ?cb1_0 - conveyorbelt)
  :precondition (and (loaded ?c ?p) (assembled ?p) (not (stored ?p)) (connected ?cb1_0 ?ct_4) (on ?c ?cb1_0))
  :effect (and (stored ?p) (empty ?c) (not (loaded ?c ?p))))
 (:action retrieve
  :parameters ( ?c - carrier ?p - product ?ct_4 - bufferstorage ?cb1_0 - conveyorbelt)
  :precondition (and (empty ?c) (stored ?p) (connected ?cb1_0 ?ct_4) (on ?c ?cb1_0))
  :effect (and (not (empty ?c)) (not (stored ?p)) (loaded ?c ?p)))
 (:action ship
  :parameters ( ?c - carrier ?p - product ?ct_5 - shipping ?cb1_0 - conveyorbelt)
  :precondition (and (loaded ?c ?p) (assembled ?p) (not (shipped ?p)) (connected ?cb1_0 ?ct_5) (on ?c ?cb1_0))
  :effect (and (not (loaded ?c ?p)) (empty ?c) (shipped ?p)))
)
