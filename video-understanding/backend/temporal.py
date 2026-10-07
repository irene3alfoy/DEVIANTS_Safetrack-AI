from collections import defaultdict
from bisect import bisect_right
import math

def timestamp(seconds):
    total = max(0, int(seconds))
    hours, remainder = divmod(total,3600)
    minutes, seconds = divmod(remainder,60)
    return f'{hours:02}:{minutes:02}:{seconds:02}' if hours else f'{minutes:02}:{seconds:02}'

def normalize(events, sample_interval):
    '''Merge only evidence-contiguous, explicitly continuous observations.
    Discrete occurrences never merge simply because their text is similar.
    '''
    output = []
    for event in sorted(events,key=lambda e:(e['start_time'],e['end_time'])):
        duplicate = next((e for e in output if e['type']==event['type'] and e['entities']==event['entities'] and e['start_time']==event['start_time'] and e['end_time']==event['end_time']),None)
        if duplicate:
            duplicate['evidence_times'] = sorted(set(duplicate['evidence_times']+event['evidence_times']))
            continue
        previous = next((e for e in reversed(output) if e['type']==event['type'] and e['entities']==event['entities'] and e['continuous'] and event['continuous'] and 0 <= event['start_time']-e['end_time'] <= sample_interval*1.1),None)
        if previous:
            previous['end_time'] = max(previous['end_time'],event['end_time'])
            previous['duration'] = previous['end_time']-previous['start_time']
            previous['confidence'] = min(previous['confidence'],event['confidence'])
            previous['identity_uncertain'] |= event['identity_uncertain']
            previous['evidence_times'] = sorted(set(previous['evidence_times']+event['evidence_times']))
        else:
            output.append(dict(event))
    for index,event in enumerate(output):
        event['id'] = f'event_{index+1}'
    return output

class TemporalEngine:
    def __init__(self, events):
        self.events = sorted(events,key=lambda e:(e['start_time'],e['end_time'],e['id']))
        self.by_id = {event['id']:event for event in self.events}

    def get_event_before(self,event):
        return [e for e in self.events if e['end_time'] < event['start_time']]

    def get_event_after(self,event):
        return [e for e in self.events if e['start_time'] > event['end_time']]

    def get_immediate_previous_event(self,event):
        before = self.get_event_before(event)
        if not before: return []
        latest = max(e['end_time'] for e in before)
        return [e for e in before if e['end_time']==latest]

    def get_immediate_next_event(self,event):
        after = self.get_event_after(event)
        if not after: return []
        earliest = min(e['start_time'] for e in after)
        return [e for e in after if e['start_time']==earliest]

    def get_events_between(self,start,end):
        return [e for e in self.events if e['start_time'] <= end and e['end_time'] >= start]

    def find_event_by_time(self,time):
        return self.get_events_between(time,time)

    def find_events_for_entity(self,entity):
        return [e for e in self.events if entity in e['entities']]

    find_entity_events = find_events_for_entity

    def find_events_before_entity_event(self,event,entity):
        return [e for e in self.get_event_before(event) if entity in e['entities']]

    def find_events_after_entity_event(self,event,entity):
        return [e for e in self.get_event_after(event) if entity in e['entities']]

    def find_first_event(self):
        return [e for e in self.events if e['start_time']==self.events[0]['start_time']] if self.events else []

    def find_last_event(self):
        latest = max((e['end_time'] for e in self.events),default=None)
        return [e for e in self.events if e['end_time']==latest]

    @staticmethod
    def count_events(events): return len(events)

    @staticmethod
    def calculate_duration(event): return event['end_time']-event['start_time']

    @staticmethod
    def compare_event_order(a,b):
        if a['end_time'] < b['start_time']: return 'BEFORE'
        if a['start_time'] > b['end_time']: return 'AFTER'
        if a['start_time'] >= b['start_time'] and a['end_time'] <= b['end_time']: return 'DURING'
        return 'OVERLAPS'

    def find_repeated_events(self):
        groups = defaultdict(list)
        for event in self.events:
            groups[(event['type'],tuple(sorted(event['entities'])))].append(event)
        return [items for items in groups.values() if len(items)>1]

    def graph(self):
        # A sparse chronological graph avoids quadratic storage for long videos.
        # Arbitrary pair relationships are computed on demand by interval rules.
        edges=[]
        starts=[e['start_time'] for e in self.events]
        for index,a in enumerate(self.events):
            if index+1 < len(self.events):
                b=self.events[index+1]
                edges.append({'event_a':a['id'],'event_b':b['id'],'relationship':self.compare_event_order(a,b)})
            next_index=bisect_right(starts,a['end_time'])
            successors=[]
            if next_index<len(self.events):
                next_start=starts[next_index]
                while next_index<len(self.events) and starts[next_index]==next_start:
                    successors.append(self.events[next_index])
                    next_index+=1
            for b in successors:
                edges.append({'event_a':a['id'],'event_b':b['id'],'relationship':'FOLLOWED_BY'})
                edges.append({'event_a':a['id'],'event_b':b['id'],'relationship':'IMMEDIATELY_BEFORE','meaning':'nearest observed successor; unobserved events may occur in sampling gaps'})
                edges.append({'event_a':b['id'],'event_b':a['id'],'relationship':'IMMEDIATELY_AFTER'})
        for group in self.find_repeated_events():
            edges.extend({'event_a':a['id'],'event_b':b['id'],'relationship':'REPEATED'} for a,b in zip(group,group[1:]))
        return edges

def event_line(event):
    interval = timestamp(event['start_time'])
    if event['end_time'] > event['start_time']:
        interval += '–'+timestamp(event['end_time'])
    return f"Approximately [{interval}] {event['description']}" + (' (identity uncertain)' if event.get('identity_uncertain') else '')

def answer_plan(plan, events, duration):
    engine = TemporalEngine(events)
    scope = f'[00:00–{timestamp(duration)}]'
    def insufficient(message):
        return {'answer':f'{scope} {message}', 'timestamps':[{'time':0,'label':'Analyzed video begins'},{'time':duration,'label':'Analyzed video ends'}], 'related_events':[], 'confidence':None, 'supported':False}
    if any(i not in engine.by_id for i in plan.anchor_ids+plan.match_ids):
        return insufficient('The requested event could not be matched reliably to the analyzed evidence.')
    matches = [engine.by_id[i] for i in plan.match_ids]
    anchors = [engine.by_id[i] for i in plan.anchor_ids]
    selected, prefix = [], ''
    operation = plan.operation
    if operation == 'unsupported':
        return insufficient((plan.reason+' ' if plan.reason else '')+'The sampled visual evidence cannot establish this. Please name a visible event or entity; sounds, causation, and unseen actions are not inferred.')
    if operation in ('first','last','sequence','repeated'):
        subset = TemporalEngine(matches if plan.filter_requested or plan.match_ids else events)
        selected = subset.find_first_event() if operation=='first' else subset.find_last_event() if operation=='last' else [e for group in subset.find_repeated_events() for e in group] if operation=='repeated' else subset.events
        prefix = {'first':'First observed event(s): ','last':'Last observed event(s): ','sequence':'Observed sequence: ','repeated':'Repeated observations: '}[operation]
    elif operation in ('before','after','immediate_before','immediate_after'):
        if len(anchors)!=1: return insufficient('Please specify exactly one reference event.')
        methods={'before':engine.get_event_before,'after':engine.get_event_after,'immediate_before':engine.get_immediate_previous_event,'immediate_after':engine.get_immediate_next_event}
        selected=methods[operation](anchors[0])
        if matches or plan.filter_requested: selected=[e for e in selected if e['id'] in plan.match_ids]
        prefix=f"Relative to {event_line(anchors[0])}: "
        if 'immediate' in operation:
            prefix+='Nearest observed event(s); sampling gaps can contain unseen actions. '
    elif operation in ('between','at'):
        start,end=plan.start_time,plan.end_time if operation=='between' else plan.start_time
        if start is None or end is None or not math.isfinite(start) or not math.isfinite(end) or not 0<=start<=end<=duration:
            return insufficient('Please specify a valid time or interval within this video.')
        selected=engine.get_events_between(start,end)
        if matches or plan.filter_requested: selected=[e for e in selected if e['id'] in plan.match_ids]
        prefix=f'Observed in [{timestamp(start)}–{timestamp(end)}]: '
    elif operation in ('gap','compare'):
        if len(anchors)!=2: return insufficient('Please specify two events to compare.')
        a,b=anchors
        selected=anchors
        if operation=='gap':
            gap=b['start_time']-a['end_time']
            prefix=f'Approximate elapsed time from the end of the first event to the start of the second: {gap:.2f} seconds. ' if gap>=0 else 'The second event does not begin after the first ends; these events overlap or occur in the reverse order. '
        else: prefix=f"The first requested event is {engine.compare_event_order(a,b).lower()} the second. "
    elif operation in ('count','duration','entity','search'):
        selected=matches
        if operation=='count': prefix=f'{len(matches)} observed occurrence(s); this is a count of sampled evidence, not a guarantee that nothing was missed. '
        if operation=='duration':
            prefix='Measured observed intervals: '
            if plan.minimum_duration is not None:
                selected=[e for e in selected if e['duration'] >= plan.minimum_duration]
    else:
        return insufficient('This temporal question could not be mapped to supported evidence.')
    if not selected:
        if anchors:
            return {'answer':prefix+'No matching event was confidently observed in that temporal relationship. This does not prove none occurred.', 'timestamps':[{'time':a['start_time'],'label':a['description']} for a in anchors], 'related_events':[a['id'] for a in anchors], 'confidence':None,'supported':False}
        return insufficient(prefix+'No matching event was confidently observed. Absence from sampled frames does not prove it never occurred.')
    selected=sorted({e['id']:e for e in selected}.values(),key=lambda e:e['start_time'])
    lines=[]
    for event in selected:
        line=event_line(event)
        if operation=='duration': line+=f"; observed duration {event['duration']:.2f} seconds"
        if operation=='entity': line+=f"; entities: {', '.join(event['entities']) or 'not reliably identified'}"
        lines.append(line)
    references=sorted({e['id']:e for e in selected+anchors}.values(),key=lambda e:e['start_time'])
    stamps=[]
    for event in references:
        stamps.append({'time':event['start_time'],'label':event['description']})
        if event['end_time']>event['start_time']:
            stamps.append({'time':event['end_time'],'label':'End: '+event['description']})
    return {'answer':prefix+'; '.join(lines), 'timestamps':stamps, 'related_events':[e['id'] for e in references], 'confidence':min(e['confidence'] for e in references),'supported':True}
