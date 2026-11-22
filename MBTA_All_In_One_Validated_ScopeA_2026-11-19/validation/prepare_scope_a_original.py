#!/usr/bin/env python3
"""Extract and audit a dated GTFS snapshot. No optimization is performed.

Accepts a GTFS ZIP, a folder of GTFS text files, or the original starter ZIP
containing one GTFS ZIP. Standard library only, Python >=3.10.
Outputs are provisional until archive applicability and operating assumptions
are reviewed. Synthetic tests are not evidence of real MBTA performance.
"""
from __future__ import annotations
import argparse
import bisect
import csv
import hashlib
import io
import json
import re
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


def gtfs_seconds(value: str) -> int:
    """Do not wrap service-day values >=24:00:00."""
    parts = str(value).split(':')
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f'Invalid GTFS clock: {value!r}')
    h, m, s = map(int, parts)
    if not 0 <= m < 60 or not 0 <= s < 60:
        raise ValueError(f'Invalid GTFS clock: {value!r}')
    return 3600*h + 60*m + s


def clock(value: int) -> str:
    h, rem = divmod(int(value), 3600)
    m, s = divmod(rem, 60)
    return f'{h:02d}:{m:02d}:{s:02d}'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


class Feed:
    def __init__(self, path: Path):
        self.path = path
        self.zips: list[zipfile.ZipFile] = []
        self.nested_name = None
        self.gtfs_sha256 = None
        if not path.exists():
            raise FileNotFoundError(f'Input not found: {path}')
        if path.is_dir():
            self.mapping = {p.name: p for p in path.rglob('*.txt')}
            self.z = None
        else:
            z = zipfile.ZipFile(path)
            self.zips.append(z)
            mapping = self._mapping(z)
            if 'stop_times.txt' not in mapping or 'trips.txt' not in mapping:
                choices = []
                for name in z.namelist():
                    if not name.lower().endswith('.zip'):
                        continue
                    blob = z.read(name)
                    inner = zipfile.ZipFile(io.BytesIO(blob))
                    self.zips.append(inner)
                    im = self._mapping(inner)
                    if 'trips.txt' in im and 'stop_times.txt' in im:
                        choices.append((name, inner, im, hashlib.sha256(blob).hexdigest()))
                if len(choices) != 1:
                    raise ValueError('Expected exactly one nested GTFS ZIP; provide the selected ZIP directly.')
                self.nested_name, z, mapping, self.gtfs_sha256 = choices[0]
            else:
                self.gtfs_sha256 = sha256(path)
            self.z, self.mapping = z, mapping
        for name in ['trips.txt', 'stop_times.txt', 'stops.txt']:
            if name not in self.mapping:
                raise ValueError(f'Missing required file: {name}')

    @staticmethod
    def _mapping(z):
        result = {}
        for name in z.namelist():
            base = Path(name).name
            if base.endswith('.txt'):
                if base in result:
                    raise ValueError(f'Duplicate GTFS filename: {base}')
                result[base] = name
        return result

    def rows(self, name):
        if name not in self.mapping:
            return
        if self.z is None:
            stream = self.mapping[name].open('r', encoding='utf-8-sig', newline='')
        else:
            stream = io.TextIOWrapper(self.z.open(self.mapping[name]), encoding='utf-8-sig', newline='')
        with stream:
            yield from csv.DictReader(stream)

    def close(self):
        for z in self.zips:
            z.close()


def active_services(calendar, exceptions, service_date: str) -> set[str]:
    d = date.fromisoformat(service_date)
    key, weekday = d.strftime('%Y%m%d'), d.strftime('%A').lower()
    active = {r['service_id'] for r in calendar
              if r.get(weekday) == '1' and r['start_date'] <= key <= r['end_date']}
    for r in exceptions:
        if r['date'] == key:
            if r['exception_type'] == '1':
                active.add(r['service_id'])
            elif r['exception_type'] == '2':
                active.discard(r['service_id'])
            else:
                raise ValueError(f"Unknown calendar exception: {r['exception_type']}")
    return active


def write_csv(path: Path, rows: list[dict], fields=None):
    fields = fields or list(dict.fromkeys(k for r in rows for k in r))
    if not fields:
        fields = ['no_records']
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='raise')
        w.writeheader()
        w.writerows(rows)


def match_waits(incoming: list[dict], outgoing: list[dict], allowance: int, penalty: int):
    """Fixed timetable evaluator: always takes earliest eligible departure.
    Penalty is never a choice when a bus remains. No capacity/other-route model.
    """
    buses = sorted(outgoing, key=lambda r: (int(r['departure_sec']), r['trip_id']))
    times = [int(r['departure_sec']) for r in buses]
    result = []
    for row in incoming:
        a = int(row['arrival_sec'])
        ready = a + allowance
        k = bisect.bisect_left(times, ready)
        stranded = k == len(times)
        dep = None if stranded else times[k]
        result.append({
            'opportunity_id': row['opportunity_id'], 'route_id': row['route_id'],
            'incoming_trip_id': row['trip_id'], 'arrival_sec': a,
            'transfer_allowance_sec': allowance, 'ready_sec': ready,
            'outgoing_trip_id': '' if stranded else buses[k]['trip_id'],
            'departure_sec': '' if stranded else dep,
            'platform_wait_sec': '' if stranded else dep-ready,
            'total_transfer_sec': '' if stranded else dep-a,
            'stranded': int(stranded),
            'waiting_cost_sec': penalty if stranded else dep-ready})
    waits = [r['platform_wait_sec'] for r in result if not r['stranded']]
    totals = [r['total_transfer_sec'] for r in result if not r['stranded']]
    summary = {
        'transfer_allowance_sec': allowance, 'opportunities': len(result),
        'served': len(waits), 'stranded': len(result)-len(waits),
        'mean_platform_wait_sec_served': statistics.mean(waits) if waits else None,
        'max_platform_wait_sec_served': max(waits) if waits else None,
        'mean_total_transfer_sec_served': statistics.mean(totals) if totals else None,
        'mean_waiting_cost_sec_all': statistics.mean([r['waiting_cost_sec'] for r in result]) if result else None,
        'penalty_sec': penalty,
        'share_with_platform_wait_le_10_min_all': sum(w <= 600 for w in waits)/len(result) if result else None,
    }
    return result, summary


def prepare(input_path: Path, output_path: Path, cfg: dict) -> dict:
    if output_path.exists() and any(output_path.iterdir()):
        raise ValueError('Output folder must be absent or empty to prevent stale-file mixing.')
    output_path.mkdir(parents=True, exist_ok=True)
    issues: list[dict[str, Any]] = []
    def issue(level, code, detail):
        issues.append({'severity': level, 'code': code, 'detail': detail})
    service_date = cfg['service_date']
    date.fromisoformat(service_date)
    start = gtfs_seconds(cfg['window_start'])
    end = gtfs_seconds(cfg['window_end'])
    if end <= start:
        raise ValueError('Study window end must exceed start.')
    for key in ['transfer_allowance_seconds', 'minimum_turnaround_seconds', 'maximum_shift_seconds',
                'headway_deviation_seconds', 'stranded_penalty_seconds']:
        if not isinstance(cfg[key], int) or cfg[key] < 0:
            raise ValueError(f'{key} must be a nonnegative integer number of seconds.')
    f = Feed(input_path)
    try:
        cal = list(f.rows('calendar.txt'))
        exc = list(f.rows('calendar_dates.txt'))
        active = active_services(cal, exc, service_date)
        if not active:
            raise ValueError('No active service IDs on requested date. Do not substitute another date silently.')
        trips = {}
        for r in f.rows('trips.txt'):
            if r['service_id'] in active:
                if r['trip_id'] in trips:
                    raise ValueError(f"Duplicate active trip_id: {r['trip_id']}")
                trips[r['trip_id']] = r
        stops = {r['stop_id']: r for r in f.rows('stops.txt')}
        focus_stops = set(map(str, cfg['ashmont_stop_ids']))
        for sid in focus_stops:
            if sid not in stops:
                issue('blocker', 'stop_not_found', sid)
            elif 'ashmont' not in stops[sid].get('stop_name', '').lower():
                issue('blocker', 'stop_name_mismatch', f'{sid}: {stops[sid].get("stop_name")}')
        route_set = set(cfg['incoming_routes']) | {cfg['outgoing_route']}
        first, last = {}, {}
        stop_rows, ash_rows = [], []
        for r in f.rows('stop_times.txt'):
            tid = r['trip_id']
            if tid not in trips:
                continue
            seq = int(r['stop_sequence'])
            if tid not in first or seq < int(first[tid]['stop_sequence']):
                first[tid] = r
            if tid not in last or seq > int(last[tid]['stop_sequence']):
                last[tid] = r
            if trips[tid]['route_id'] in route_set:
                stop_rows.append(r)
                if r['stop_id'] in focus_stops:
                    ash_rows.append(r)
        seen = set()
        for r in stop_rows:
            key = (r['trip_id'], r['stop_sequence'])
            if key in seen:
                issue('blocker', 'duplicate_stop_time_key', str(key))
            seen.add(key)
        endpoints = {}
        for tid, t in trips.items():
            if tid not in first:
                continue
            a, b = first[tid], last[tid]
            try:
                endpoints[tid] = {
                    'trip_id': tid, 'route_id': t['route_id'], 'service_id': t['service_id'],
                    'block_id': t.get('block_id', ''),
                    'start_stop_id': a['stop_id'], 'end_stop_id': b['stop_id'],
                    'start_sec': gtfs_seconds(a['departure_time']),
                    # Conservative public-schedule occupation end includes any final scheduled dwell.
                    'end_sec': max(gtfs_seconds(b['arrival_time']), gtfs_seconds(b['departure_time'])),
                    'end_arrival_sec': gtfs_seconds(b['arrival_time']),
                    'first_sequence': int(a['stop_sequence']), 'last_sequence': int(b['stop_sequence'])}
            except (ValueError, KeyError):
                # A relevant block with missing endpoints is explicitly blocked below.
                continue
        events, incoming, outgoing = [], [], []
        regex = re.compile(cfg['outgoing_headsign_regex'], re.I)
        for r in ash_rows:
            t = trips[r['trip_id']]
            tid = t['trip_id']
            if tid not in endpoints:
                issue('blocker', 'focus_trip_missing_endpoint_time', tid)
                continue
            e = endpoints[tid]
            try:
                arr, dep = gtfs_seconds(r['arrival_time']), gtfs_seconds(r['departure_time'])
            except ValueError:
                issue('blocker', 'focus_stop_missing_time', tid)
                continue
            seq = int(r['stop_sequence'])
            is_first, is_last = seq == e['first_sequence'], seq == e['last_sequence']
            ev = {
                'service_date': service_date, 'trip_id': tid, 'route_id': t['route_id'],
                'service_id': t['service_id'], 'direction_id': t.get('direction_id', ''),
                'trip_headsign': t.get('trip_headsign', ''), 'block_id': t.get('block_id', ''),
                'stop_id': r['stop_id'], 'stop_sequence': seq,
                'arrival_sec': arr, 'departure_sec': dep,
                'arrival_time': r['arrival_time'], 'departure_time': r['departure_time'],
                'pickup_type': r.get('pickup_type', '') or '0',
                'drop_off_type': r.get('drop_off_type', '') or '0',
                'is_first_stop': int(is_first), 'is_last_stop': int(is_last)}
            events.append(ev)
            # Ordinary fixed-route boarding/alighting only; conditional pickup needs separate analysis.
            if t['route_id'] in cfg['incoming_routes'] and is_last and start <= arr < end:
                if ev['drop_off_type'] != '0':
                    issue('blocker', 'incoming_alighting_not_ordinary', tid)
                    continue
                incoming.append(dict(ev, opportunity_id=f'{service_date}:{tid}:{seq}'))
            if t['route_id'] == cfg['outgoing_route'] and is_first and regex.search(t.get('trip_headsign', '')):
                if ev['pickup_type'] != '0':
                    issue('blocker', 'outgoing_boarding_not_ordinary', tid)
                    continue
                outgoing.append(dict(ev, is_adjustable=int(start <= dep < end)))
        incoming.sort(key=lambda r: (r['arrival_sec'], r['trip_id']))
        outgoing.sort(key=lambda r: (r['departure_sec'], r['trip_id']))
        if not incoming or not outgoing:
            issue('blocker', 'empty_cohort_or_outgoing', f'incoming={len(incoming)}, outgoing={len(outgoing)}')
        incoming_counts = dict(Counter(r['route_id'] for r in incoming))
        expected = cfg.get('expected_counts_from_prior_notes', {})
        for route, n in expected.get('incoming', {}).items():
            if incoming_counts.get(route, 0) != n:
                issue('review', 'prior_count_discrepancy', f'route {route}: found {incoming_counts.get(route,0)}; prior notes {n}')
        adjustable = {r['trip_id'] for r in outgoing if r['is_adjustable']}
        if 'adjustable_outgoing' in expected and len(adjustable) != expected['adjustable_outgoing']:
            issue('review', 'prior_count_discrepancy', f'adjustable outgoing: found {len(adjustable)}; prior notes {expected["adjustable_outgoing"]}')
        if len({r['trip_id'] for r in incoming}) != len(incoming):
            issue('blocker', 'multiple_opportunities_per_incoming_trip', 'Review repeated Ashmont terminal records.')
        blocks = {trips[tid].get('block_id', '') for tid in adjustable} - {''}
        block_trips = [t for t in trips.values() if t.get('block_id', '') in blocks]
        for t in block_trips:
            if t['trip_id'] not in endpoints:
                issue('blocker', 'block_trip_missing_endpoint', t['trip_id'])
        for tid in adjustable:
            if not trips[tid].get('block_id'):
                issue('blocker', 'adjustable_trip_missing_block', tid)
        chains = defaultdict(list)
        for t in block_trips:
            if t['trip_id'] in endpoints:
                chains[t['block_id']].append(endpoints[t['trip_id']])
        limit, turn = cfg['maximum_shift_seconds'], cfg['minimum_turnaround_seconds']
        bounds = {tid: {'trip_id':tid, 'lower_shift_sec':-limit, 'upper_shift_sec':limit,
                        'bounds_complete':True} for tid in adjustable}
        overrides = cfg.get('deadhead_seconds_by_stop_pair', {})
        links = []
        for block, chain in chains.items():
            chain.sort(key=lambda r: (r['start_sec'], r['trip_id']))
            for p, q in zip(chain, chain[1:]):
                relevant = p['trip_id'] in adjustable or q['trip_id'] in adjustable
                if not relevant:
                    continue
                pair = p['end_stop_id']+'->'+q['start_stop_id']
                deadhead = 0 if p['end_stop_id'] == q['start_stop_id'] else overrides.get(pair)
                if deadhead is not None and (not isinstance(deadhead, int) or deadhead < 0):
                    raise ValueError(f'Invalid deadhead seconds for {pair}')
                required = None if deadhead is None else deadhead+turn
                gap = q['start_sec']-p['end_sec']
                links.append({'block_id':block, 'predecessor_trip_id':p['trip_id'],
                              'successor_trip_id':q['trip_id'],
                              'predecessor_route_id':p['route_id'], 'successor_route_id':q['route_id'],
                              'predecessor_end_stop_id':p['end_stop_id'], 'successor_start_stop_id':q['start_stop_id'],
                              'predecessor_end_sec':p['end_sec'], 'successor_start_sec':q['start_sec'],
                              'scheduled_gap_sec':gap,
                              'gap_from_last_arrival_sec':q['start_sec']-p['end_arrival_sec'],
                              'minimum_turnaround_sec':turn,
                              'deadhead_sec':deadhead, 'minimum_gap_sec':required,
                              'predecessor_adjustable':int(p['trip_id'] in adjustable),
                              'successor_adjustable':int(q['trip_id'] in adjustable)})
                if required is None:
                    issue('blocker', 'unknown_deadhead', pair)
                    for tid in (p['trip_id'], q['trip_id']):
                        if tid in bounds:
                            bounds[tid]['bounds_complete'] = False
                    continue
                if gap < required:
                    issue('review', 'baseline_vehicle_infeasible_under_assumptions', f"{p['trip_id']}->{q['trip_id']}: gap {gap}, required {required}")
                if q['trip_id'] in adjustable and p['trip_id'] not in adjustable:
                    bounds[q['trip_id']]['lower_shift_sec'] = max(-limit, required-gap)
                if p['trip_id'] in adjustable and q['trip_id'] not in adjustable:
                    bounds[p['trip_id']]['upper_shift_sec'] = min(limit, gap-required)
            for endpoint in [chain[0], chain[-1]]:
                if endpoint['trip_id'] in adjustable:
                    issue('review', 'block_boundary_not_depot_verified', endpoint['trip_id'])
        for row in bounds.values():
            if row['lower_shift_sec'] > row['upper_shift_sec']:
                issue('blocker', 'empty_individual_shift_interval', row['trip_id'])
        headways = []
        slack = cfg['headway_deviation_seconds']
        for p, q in zip(outgoing, outgoing[1:]):
            if not (p['is_adjustable'] or q['is_adjustable']):
                continue
            gap = q['departure_sec']-p['departure_sec']
            headways.append({'earlier_trip_id':p['trip_id'], 'later_trip_id':q['trip_id'],
                             'scheduled_headway_sec':gap, 'minimum_headway_sec':max(1,gap-slack),
                             'maximum_headway_sec':gap+slack,
                             'basis':'Assumption: preserve each original headway within configured deviation.'})
            if gap < 1:
                issue('blocker', 'nonpositive_headway', f"{p['trip_id']}->{q['trip_id']}")
        selected_stop_rows = [r for r in stop_rows if r['trip_id'] in adjustable]
        grouped = defaultdict(list)
        for r in selected_stop_rows:
            grouped[r['trip_id']].append(r)
        for tid, rows in grouped.items():
            previous = -1
            for r in sorted(rows, key=lambda r:int(r['stop_sequence'])):
                try:
                    a, d = gtfs_seconds(r['arrival_time']), gtfs_seconds(r['departure_time'])
                    if not previous <= a <= d:
                        issue('blocker', 'nonmonotone_selected_trip', f'{tid}:{r["stop_sequence"]}')
                    previous = d
                except ValueError:
                    issue('review', 'selected_trip_intermediate_time_missing', f'{tid}:{r["stop_sequence"]}')
        station_ids = {sid for sid,s in stops.items() if 'ashmont' in s.get('stop_name','').lower()} | focus_stops
        station_ids |= {s.get('parent_station','') for sid,s in stops.items() if sid in station_ids}
        station_ids.discard('')
        station_ids |= {sid for sid,s in stops.items() if s.get('parent_station') in station_ids}
        transfers = [r for r in f.rows('transfers.txt') if
                     (r.get('from_stop_id') in station_ids and r.get('to_stop_id') in station_ids)
                     or r.get('from_trip_id') in {t['trip_id'] for t in block_trips}
                     or r.get('to_trip_id') in {t['trip_id'] for t in block_trips}]
        if any(r.get('transfer_type') in ('3','4','5') for r in transfers):
            issue('review', 'restricted_or_linked_transfer_records', 'Review transfer prohibitions and linked-trip rules. They are exported, not auto-applied.')
        paths = [r for r in f.rows('pathways.txt') if r.get('from_stop_id') in station_ids and r.get('to_stop_id') in station_ids]
        feed_info = list(f.rows('feed_info.txt'))
        for r in feed_info:
            key = service_date.replace('-','')
            if r.get('feed_start_date') and key < r['feed_start_date']:
                issue('blocker', 'date_before_feed_coverage', r['feed_start_date'])
            if r.get('feed_end_date') and key > r['feed_end_date']:
                issue('blocker', 'date_after_feed_coverage', r['feed_end_date'])
        issue('review', 'archive_applicability_unverified', 'Calendar validity is not proof this publication was in force on this date. Compare the LAMP archive.')
        issue('review', 'operating_assumptions_not_certified', 'Transfer time, turnaround and headway limits are explicit assumptions, not verified MBTA rules.')
        issue('review', 'public_vehicle_blocks_only', 'Crew, garage movements, cross-service-day links and operational dispatch are outside this extraction.')
        issue('review', 'transfer_rules_manual_review', 'Raw transfers/pathways are exported. Confirm applicable rule specificity and boarding locations before finalizing the allowance.')
        write_csv(output_path/'incoming.csv', incoming)
        write_csv(output_path/'outgoing.csv', outgoing)
        write_csv(output_path/'ashmont_all_route_events.csv', sorted(events,key=lambda r:(r['departure_sec'],r['trip_id'])))
        write_csv(output_path/'vehicle_links.csv', links)
        write_csv(output_path/'block_trip_endpoints.csv', [e for e in endpoints.values() if e['block_id'] in blocks])
        write_csv(output_path/'shift_bounds.csv', sorted(bounds.values(),key=lambda r:r['trip_id']))
        write_csv(output_path/'headway_limits.csv', headways)
        write_csv(output_path/'selected_trip_stop_times.csv', selected_stop_rows)
        write_csv(output_path/'ashmont_stops.csv', [s for sid,s in stops.items() if sid in station_ids])
        write_csv(output_path/'transfers_for_review.csv', transfers)
        write_csv(output_path/'pathways_for_review.csv', paths)
        write_csv(output_path/'feed_info.csv', feed_info)
        waits, summary = match_waits(incoming, outgoing, cfg['transfer_allowance_seconds'], cfg['stranded_penalty_seconds'])
        write_csv(output_path/'baseline_connections.csv', waits)
        sensitivity = []
        for tau in sorted(set(cfg.get('transfer_sensitivity_seconds', [])+[cfg['transfer_allowance_seconds']])):
            if not isinstance(tau,int) or tau < 0:
                raise ValueError('Sensitivity allowances must be nonnegative integer seconds.')
            _, stats = match_waits(incoming, outgoing, tau, cfg['stranded_penalty_seconds'])
            sensitivity.append(stats)
        write_csv(output_path/'baseline_transfer_sensitivity.csv', sensitivity)
        (output_path/'baseline_metrics.json').write_text(json.dumps(summary,indent=2))
        write_csv(output_path/'quality_issues.csv', issues, ['severity','code','detail'])
        audit = {'status':'BLOCKED' if any(r['severity']=='blocker' for r in issues) else 'PROVISIONAL_REQUIRES_REVIEW',
                 'created_utc':datetime.now(timezone.utc).isoformat(), 'service_date':service_date,
                 'source_input_name':input_path.name,
                 'source_sha256':sha256(input_path) if input_path.is_file() else None,
                 'nested_gtfs_name':f.nested_name, 'gtfs_sha256':f.gtfs_sha256,
                 'active_service_ids':sorted(active), 'incoming_counts':incoming_counts,
                 'outgoing_all_day_count':len(outgoing), 'adjustable_outgoing_count':len(adjustable),
                 'post_window_outgoing_count':sum(r['departure_sec']>=end for r in outgoing),
                 'issues':issues, 'config':cfg,
                 'warning':'Computed from supplied input. Not proof of historical applicability or operational approval.'}
        (output_path/'audit.json').write_text(json.dumps(audit,indent=2))
        (output_path/'config_used.json').write_text(json.dumps(cfg,indent=2))
        return audit
    finally:
        f.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--config', type=Path, default=Path(__file__).with_name('config.json'))
    args = p.parse_args()
    try:
        audit = prepare(args.input, args.out, json.loads(args.config.read_text()))
        print(json.dumps({k:audit[k] for k in ['status','incoming_counts','outgoing_all_day_count','adjustable_outgoing_count']},indent=2))
        return 2 if audit['status']=='BLOCKED' else 0
    except (ValueError,KeyError,OSError,zipfile.BadZipFile) as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
