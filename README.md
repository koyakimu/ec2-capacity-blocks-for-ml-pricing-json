# EC2 Capacity Blocks for ML Pricing JSON

Amazon EC2 Capacity Blocks for MLの料金データを自動取得してJSON形式で提供するリポジトリです。

## 免責事項

このリポジトリで提供される情報は非公式なものであり、AWS公式の情報ではありません。データの正確性については保証されず、利用は自己責任でお願いします。最新かつ正確な料金情報については、必ずAWS公式サイトをご確認ください。

## データソース

- **URL**: https://aws.amazon.com/ec2/capacityblocks/pricing/
- **更新頻度**: 毎月1日（GitHub Actionsによる自動更新）

## 出力ファイル

料金データは `data/pricing.json` に出力されます。

### JSON構造

```json
{
  "metadata": {
    "last_updated": "2026-01-31T14:30:00Z",
    "source_url": "https://aws.amazon.com/ec2/capacityblocks/pricing/",
    "version": "1.0.0"
  },
  "instance_types": {
    "p5.48xlarge": {
      "instance_family": "P5",
      "accelerator_type": "H100",
      "accelerator_count": 8,
      "pricing": [
        {
          "region": "US East (N. Virginia)",
          "region_code": "us-east-1",
          "hourly_rate_usd": 31.464,
          "accelerator_hourly_rate_usd": 3.933
        }
      ]
    }
  }
}
```

## 対応インスタンスタイプ

| ファミリー | インスタンスタイプ | アクセラレータ |
|-----------|-------------------|---------------|
| P6e | u-p6e-gb200x72, u-p6e-gb200x36 | GB200 |
| P6-B300 | p6-b300.48xlarge | B300 |
| P6-B200 | p6-b200.48xlarge | B200 |
| P5en | p5en.48xlarge | H200 |
| P5e | p5e.48xlarge | H200 |
| P5 | p5.48xlarge, p5.4xlarge | H100 |
| P4de | p4de.24xlarge | A100 |
| P4d | p4d.24xlarge | A100 |
| Trn2 | trn2.48xlarge, trn2.3xlarge | Trainium2 |
| Trn1 | trn1.32xlarge | Trainium |

## ローカル実行

```bash
# uvを使用する場合（推奨）
uv run python -m src.scraper

# pipを使用する場合
pip install -r requirements.txt
python -m src.scraper
```

## ライセンス

MIT License
