# fill_db_script.py

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel

from app.base.models import Video, VideoSnapshot
from app.base.session_maker import database_manager


class SnapshotIn(BaseModel):
    id: UUID
    video_id: UUID
    views_count: int
    likes_count: int
    reports_count: int
    comments_count: int
    delta_views_count: int
    delta_likes_count: int
    delta_reports_count: int
    delta_comments_count: int
    created_at: datetime
    updated_at: datetime


class VideoIn(BaseModel):
    id: UUID
    video_created_at: datetime
    views_count: int
    likes_count: int
    reports_count: int
    comments_count: int
    creator_id: str
    created_at: datetime
    updated_at: datetime
    snapshots: List[SnapshotIn] = []


async def fill_db(path: str, batch_size: int = 500) -> None:
    path_json = Path(path)

    with path_json.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    raw_videos = raw.get("videos", [])
    if not raw_videos:
        print("пустой videos в json’е")
        return

    total_videos = 0
    total_snaps = 0

    async with database_manager.create_session() as session:
        to_add = []

        for video_raw in raw_videos:
            video_in = VideoIn.model_validate(video_raw)

            video = Video(**video_in.model_dump(exclude={"snapshots"}))
            to_add.append(video)
            total_videos += 1

            for snap_in in video_in.snapshots:
                snapshot = VideoSnapshot(**snap_in.model_dump())
                to_add.append(snapshot)
                total_snaps += 1

            if len(to_add) >= batch_size:
                session.add_all(to_add)
                await session.commit()
                to_add.clear()
                print(f"батч: видео={total_videos}, снапы={total_snaps}")

        if to_add:
            session.add_all(to_add)
            await session.commit()
            print(f"финал: видео={total_videos}, снапы={total_snaps}")

    print(f"ГОТОВО. видео={total_videos}, снапы={total_snaps}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit(1)

    asyncio.run(fill_db(sys.argv[1]))
