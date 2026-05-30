#!/usr/bin/env python3
"""Upload the 美少女万華鏡 voice dataset to HuggingFace."""

import sys, os, csv

def main():
    print("=== 上传 美少女万華鏡 语音数据集到 HuggingFace ===\n")

    # 1. Auth
    print("[1/3] 登录 HuggingFace...")
    try:
        from huggingface_hub import login, HfApi, create_repo
    except ImportError:
        print("请先安装: .venv/Scripts/pip.exe install huggingface_hub")
        sys.exit(1)

    repo = "dddd109/biman-voice-dataset"
    dataset_dir = "D:/GAL_unpack/dataset"

    # Login (will prompt for token)
    login()

    # 2. Create repo
    print(f"\n[2/3] 创建仓库: {repo}")
    api = HfApi()
    url = create_repo(repo, repo_type="dataset", exist_ok=True)

    # 3. Upload
    print(f"\n[3/3] 上传 {dataset_dir}/ ...")
    print("  (CSV 文件 + OGG 音频, 可能需要几分钟)")

    # Build README for the dataset
    readme = """---
license: cc-by-nc-4.0
task_categories:
- text-to-speech
- audio-text
language:
- ja
tags:
- tts
- anime
- vits
- galgame
pretty_name: 美少女万華鏡 Voice Dataset
size_categories:
- 10K<n<100K
---

# 美少女万華鏡 (Bishoujo Mangekyou) Voice Dataset

Voice-text pairs extracted from the 美少女万華鏡 visual novel series (games 1-5).

## Summary

- **Total**: 19,875 utterances across 90 characters
- **Main character (蓮華/Renge)**: 3,670 utterances
- **Format**: OGG 44.1kHz mono, CSV with game/voice_id/audio_path/text
- **Language**: Japanese (日本語)
- **Source**: 美少女万華鏡 1-5 (ωstar)

## Characters

| ID | Name | Lines |
|----|------|------:|
| reng | 蓮華 (Renge) | 3,670 |
| yuma | 覡夕摩 (Yuuma) | 3,074 |
| yuri | 覡夕莉 (Yuuri) | 2,631 |
| alic | アリス (Alice) | 2,537 |
| doro | ドロシー (Dorothy) | 2,392 |
| kiri | キリエ (Kirie) | 2,255 |

...and 84 more characters.

## Usage

Each CSV file contains: `game, voice_id, audio_path, text`

```python
import csv
with open("reng.csv", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        audio = row["audio_path"]  # absolute path to .ogg file
        text = row["text"]          # Japanese transcript
```

## License

This dataset is extracted from copyrighted game content. Use for research and non-commercial purposes only.
"""

    with open(dataset_dir + "/README.md", "w", encoding="utf-8") as f:
        f.write(readme)

    api.upload_folder(
        folder_path=dataset_dir,
        path_in_repo=".",
        repo_id=repo,
        repo_type="dataset",
    )

    print(f"\n✓ 上传完成!")
    print(f"  https://huggingface.co/datasets/{repo}")


if __name__ == "__main__":
    main()
