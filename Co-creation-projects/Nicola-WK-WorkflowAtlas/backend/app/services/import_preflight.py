"""Read-only preflight of immutable identities; no guessed repairs or writes."""
from collections import defaultdict
import hashlib

from ..schemas import ImportIssue, StandardMessage
from ..storage import dump, message_fingerprint


def decode_import(data: bytes) -> str:
    try:
        if data.startswith((b'\xff\xfe\x00\x00', b'\x00\x00\xfe\xff')):
            return data.decode('utf-32')
        if data.startswith((b'\xff\xfe', b'\xfe\xff')):
            return data.decode('utf-16')
        try:
            return data.decode('utf-8-sig')
        except UnicodeError:
            return data.decode('gb18030')
    except UnicodeError:
        raise ValueError('文件编码无法识别，支持 UTF-8、带 BOM 的 UTF-16/32 和 GB18030/GBK。') from None


def import_warnings(messages: list[StandardMessage]) -> list[str]:
    warnings = []
    for message in messages:
        details = message.metadata.get('import', {})
        if isinstance(details, dict) and details.get('identity_kind') == 'derived':
            warnings.append('部分导出记录没有平台消息 ID，已按原始记录生成本地去重标识；标识类型和生成依据保留在元数据中。')
            break
    for message in messages:
        details = message.metadata.get('import', {})
        raw = message.metadata.get('raw', {})
        kind = details.get('message_kind') if isinstance(details, dict) else None
        if kind is None:
            kind = raw.get('msg_type', 'text') if isinstance(raw, dict) else 'text'
        if kind not in {'text', 'post', 'link', 'system'}:
            warnings.append('图片、音视频、文件等非文本消息仅保留原始元数据与占位文本，未读取附件内容。')
            break
    return warnings


def preview_import(repository, content: str, source_id: str, format: str, naive_timezone: str):
    from ..connectors.preview import preview_messages
    preview = preview_messages(content, source_id, format, naive_timezone)
    groups = defaultdict(list)
    for index, message in enumerate(preview.messages):
        groups[message.id].append((index, message))
    existing = {}
    ids = list(groups)
    with repository.lock:
        for start in range(0, len(ids), 500):
            chunk = ids[start:start + 500]
            marks = ','.join('?' for _ in chunk)
            for row in repository.connection.execute('SELECT id,payload FROM messages WHERE source_id=? AND id IN (' + marks + ')', (source_id, *chunk)):
                existing[row['id']] = StandardMessage.model_validate_json(row['payload'])
    accepted, accepted_indices, duplicates, new = [], [], 0, 0
    for identity, candidates in groups.items():
        representative = candidates[0][1]
        versions = {message_fingerprint(message) for _, message in candidates}
        conflict = len(versions) > 1 or (identity in existing and message_fingerprint(existing[identity]) != message_fingerprint(representative))
        if conflict:
            for index, message in candidates:
                preview.issues.append(ImportIssue(
                    position=preview.candidate_positions[index], line=preview.candidate_lines[index], field='id', code='immutable_conflict',
                    detail='同一消息标识对应不同内容或已有记录，不能覆盖；请核对问题记录。', raw=preview.candidate_raw[index]))
            continue
        accepted.append(representative)
        accepted_indices.append(candidates[0][0])
        duplicates += len(candidates) if identity in existing else len(candidates) - 1
        new += identity not in existing
    preview.messages, preview.valid = accepted, len(accepted)
    preview.candidate_positions = [preview.candidate_positions[i] for i in accepted_indices]
    preview.candidate_lines = [preview.candidate_lines[i] for i in accepted_indices]
    preview.candidate_raw = [preview.candidate_raw[i] for i in accepted_indices]
    preview.duplicates, preview.imported_candidates = duplicates, new
    preview.issues.sort(key=lambda issue: (issue.position, issue.field))
    preview.fingerprint = hashlib.sha256(dump([source_id, format, naive_timezone, content,
        [message.model_dump(mode='json') for message in accepted]]).encode('utf-8')).hexdigest()
    preview.warnings = list(dict.fromkeys([*preview.warnings, *import_warnings(accepted)]))
    return preview
