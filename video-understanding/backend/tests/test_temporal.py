from backend.temporal import TemporalEngine, normalize, answer_plan, timestamp
from backend.vision import QueryPlan

def event(id,start,end,type='move',entities=None,continuous=False):
    return dict(id=id,type=type,description=f'Observed {id}',start_time=start,end_time=end,duration=end-start,entities=entities or ['Object_01'],confidence=.9,identity_uncertain=False,continuous=continuous,evidence_times=[start,end])

def test_timestamp_hours_and_no_rollover():
    assert timestamp(3600)=='01:00:00'
    assert timestamp(59.9)=='00:59'
    assert timestamp(3661.1)=='01:01:01'

def test_order_uses_end_times_not_only_start():
    events=[event('a',10,40),event('b',20,22),event('c',45,47)]
    engine=TemporalEngine(events)
    assert engine.compare_event_order(events[1],events[0])=='DURING'
    assert engine.get_event_before(events[1])==[]
    assert engine.get_immediate_previous_event(events[2])==[events[0]]
    assert engine.get_immediate_next_event(events[0])==[events[2]]
    assert engine.get_events_between(21,23)==events[:2]

def test_nearest_observation_ties_return_all():
    events=[event('a',1,3),event('b',2,3),event('c',7,8)]
    assert len(TemporalEngine(events).get_immediate_previous_event(events[2]))==2

def test_continuous_merging_does_not_collapse_repeated_stops():
    items=[event('a',0,2,continuous=True),event('b',4,6,continuous=True),event('c',8,8,type='stop'),event('d',10,10,type='stop')]
    result=normalize(items,2)
    assert len(result)==3
    assert result[0]['duration']==6
    assert len(TemporalEngine(result).find_repeated_events()[0])==2

def test_entity_aware_counts():
    events=[event('a',1,1),event('b',2,2,entities=['Object_02']),event('c',3,3)]
    assert len(TemporalEngine(events).find_repeated_events()[0])==2
    result=answer_plan(QueryPlan(operation='count',match_ids=['a','c']),events,10)
    assert result['answer'].startswith('2 observed')
    assert len(result['timestamps'])==2

def test_false_after_premise_is_not_reversed():
    events=[event('person',42,42),event('truck',78,78)]
    answer=answer_plan(QueryPlan(operation='after',anchor_ids=['truck'],match_ids=['person']),events,100)
    assert not answer['supported']
    assert 'No matching event' in answer['answer']
    assert '01:18' in answer['answer']
    assert answer['timestamps'][0]['time']==78

def test_gap_and_duration_are_computed_from_intervals():
    events=[event('a',10,14),event('b',20,28)]
    answer=answer_plan(QueryPlan(operation='gap',anchor_ids=['a','b']),events,60)
    assert '6.00 seconds' in answer['answer']
    answer=answer_plan(QueryPlan(operation='duration',match_ids=['b']),events,60)
    assert '8.00 seconds' in answer['answer']
    assert [t['time'] for t in answer['timestamps']]==[20,28]

def test_unknown_ids_fail_closed_with_coverage_timestamps():
    answer=answer_plan(QueryPlan(operation='before',anchor_ids=['invented']),[event('a',10,14)],120)
    assert not answer['supported']
    assert '[00:00–02:00]' in answer['answer']
    assert answer['related_events']==[]

def test_no_events_and_unsupported_have_timestamps_without_claims():
    for operation in ('search','unsupported','first','count'):
        result=answer_plan(QueryPlan(operation=operation),[],90)
        assert result['timestamps']
        assert '[00:00–01:30]' in result['answer']
        assert not result['supported']

def test_invalid_time_interval_is_rejected():
    result=answer_plan(QueryPlan(operation='between',start_time=20,end_time=10),[],90)
    assert not result['supported']

def test_find_entity_events_and_last():
    events=[event('a',0,30),event('b',20,22,entities=['Object_02'])]
    engine=TemporalEngine(events)
    assert engine.find_last_event()==[events[0]]
    assert engine.find_events_for_entity('Object_02')==[events[1]]

def test_missing_filter_never_becomes_unrestricted_query():
    events=[event('a',1,1),event('b',3,3)]
    for operation in ('first','last','sequence','repeated'):
        result=answer_plan(QueryPlan(operation=operation,filter_requested=True),events,10)
        assert not result['supported']
        assert result['related_events']==[]
    result=answer_plan(QueryPlan(operation='after',anchor_ids=['a'],filter_requested=True),events,10)
    assert not result['supported']
    assert result['related_events']==['a']
