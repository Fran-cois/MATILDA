# 🗄️ Large-Scale Datasets for MATILDA

This directory contains large-scale synthetic and real-world datasets for stress testing MATILDA's scalability.

## 📊 Dataset Categories

### 1. Synthetic Datasets (Generated)
- **dataset_1M.db** - 1 million tuples
- **dataset_5M.db** - 5 million tuples
- **dataset_10M.db** - 10 million tuples
- **dataset_50M.db** - 50 million tuples (optional)

### 2. Real-World Datasets (External)
- **IMDB** - Movie database (~5M tuples)
- **WikiData** - Knowledge graph subset (~10M tuples)
- **YAGO** - Semantic knowledge base (~20M tuples)

---

## 🔨 Generating Synthetic Datasets

### Quick Start

```bash
# Generate 1M tuple dataset (default)
python scripts/utils/generate_large_dataset.py data/large_scale/dataset_1M.db

# Generate 5M tuple dataset
python scripts/utils/generate_large_dataset.py data/large_scale/dataset_5M.db --tuples 5000000

# Generate 10M tuples, 10 tables, 8 columns each
python scripts/utils/generate_large_dataset.py data/large_scale/dataset_10M.db \
  --tuples 10000000 --tables 10 --columns 8
```

### Generator Options

| Option | Default | Description |
|--------|---------|-------------|
| `--tuples` | 1,000,000 | Total number of tuples across all tables |
| `--tables` | 5 | Number of tables to create |
| `--columns` | 5 | Columns per table (including ID) |
| `--no-relationships` | False | Disable foreign key relationships |
| `--seed` | 42 | Random seed for reproducibility |

### Schema Structure

Generated datasets have:
- **Tables**: Table1, Table2, ..., TableN
- **Columns**: 
  - `id` (INTEGER PRIMARY KEY)
  - `col1`, `col2`, ... (INTEGER/TEXT/REAL)
- **Relationships**: Foreign keys from Table{i+1} → Table{i}

---

## 📥 Downloading Real-World Datasets

### IMDB Dataset

```bash
# Download IMDB dataset
wget https://datasets.imdbws.com/title.basics.tsv.gz
wget https://datasets.imdbws.com/title.ratings.tsv.gz
wget https://datasets.imdbws.com/name.basics.tsv.gz

# Convert to SQLite (requires conversion script)
python scripts/utils/convert_imdb_to_sqlite.py \
  --input title.basics.tsv.gz title.ratings.tsv.gz name.basics.tsv.gz \
  --output data/large_scale/imdb.db
```

### WikiData/YAGO

```bash
# Download WikiData subset (RDF format)
wget https://dumps.wikimedia.org/wikidatawiki/entities/latest-truthy.nt.gz

# Convert to SQLite (requires RDF conversion)
# python scripts/utils/convert_rdf_to_sqlite.py ...
```

---

## 🔍 Dataset Statistics

### View Dataset Info

```bash
# Show statistics of generated dataset
python scripts/utils/generate_large_dataset.py data/large_scale/dataset_1M.db --stats-only
```

**Example Output:**
```
================================================================================
📊 DATABASE STATISTICS
================================================================================
  Table1               200,000 rows
  Table2               200,000 rows
  Table3               200,000 rows
  Table4               200,000 rows
  Table5               200,000 rows
================================================================================
  Total Tables:        5
  Total Tuples:        1,000,000
  Database Size:       87.34 MB
================================================================================
```

---

## ⚡ Performance Benchmarks

### Expected Generation Times

| Dataset Size | Tables | Time (approx) | Disk Size |
|-------------|--------|---------------|-----------|
| 1M tuples   | 5      | ~30 seconds   | ~90 MB    |
| 5M tuples   | 5      | ~2.5 minutes  | ~450 MB   |
| 10M tuples  | 10     | ~7 minutes    | ~1.2 GB   |
| 50M tuples  | 10     | ~40 minutes   | ~6 GB     |

*Times measured on standard laptop (Intel i7, 16GB RAM)*

---

## 🎯 Use Cases

### 1. Scalability Testing (T3.2)
```bash
# Run stress test on 1M dataset
python scripts/benchmarks/stress_test.py data/large_scale/dataset_1M.db

# Compare with baseline
python scripts/benchmarks/stress_test.py data/large_scale/dataset_1M.db --baseline anyburl
```

### 2. Memory Profiling
```bash
# Monitor memory usage during discovery
python scripts/utils/monitor_resources.py \
  --command "python src/main.py --db data/large_scale/dataset_5M.db" \
  --output results/monitoring_5M.json
```

### 3. Algorithm Comparison
```bash
# Compare MATILDA vs baselines on large dataset
python cli.py benchmark --full --dataset data/large_scale/dataset_10M.db
```

---

## 📝 Best Practices

### Dataset Selection

1. **Small Tests** (1M tuples)
   - Quick validation
   - Algorithm debugging
   - CI/CD tests

2. **Medium Tests** (5M tuples)
   - Performance benchmarks
   - Memory profiling
   - Comparison with baselines

3. **Large Tests** (10M+ tuples)
   - Scalability proof
   - Production readiness
   - Thesis validation

### Resource Requirements

| Dataset | Min RAM | Recommended RAM | Disk Space |
|---------|---------|-----------------|------------|
| 1M      | 4 GB    | 8 GB            | 500 MB     |
| 5M      | 8 GB    | 16 GB           | 2 GB       |
| 10M     | 16 GB   | 32 GB           | 5 GB       |
| 50M     | 32 GB   | 64 GB           | 20 GB      |

---

## 🔧 Troubleshooting

### Out of Memory

```bash
# Reduce number of concurrent operations
export OMP_NUM_THREADS=1

# Use swap space
sudo sysctl -w vm.overcommit_memory=1

# Generate smaller batches
python scripts/utils/generate_large_dataset.py dataset.db --tuples 1000000
```

### Slow Generation

```bash
# Use SSD for better I/O
# Increase batch size in generator
# Disable foreign key constraints temporarily
```

### Disk Space Issues

```bash
# Check available space
df -h

# Clean old datasets
rm data/large_scale/dataset_old_*.db

# Compress archives
gzip data/large_scale/dataset_10M.db
```

---

## 📚 References

- [SQLite Performance](https://www.sqlite.org/performance.html)
- [Large Dataset Best Practices](https://www.sqlite.org/intern-v-extern-blob.html)
- [IMDB Datasets](https://www.imdb.com/interfaces/)
- [WikiData Dumps](https://dumps.wikimedia.org/wikidatawiki/)

---

*Last updated: 19 janvier 2026*
