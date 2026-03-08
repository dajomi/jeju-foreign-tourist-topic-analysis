import os
import re
import glob
import warnings
from pathlib import Path

import pandas as pd
import numpy as np

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

from gensim import corpora
from gensim.models import LdaModel

warnings.filterwarnings("ignore")


nltk.download("stopwords")
nltk.download("wordnet")
nltk.download("omw-1.4")

INPUT_DIR = r"./data/장소별_리뷰(중복,한국어제외)"
OUTPUT_DIR = os.path.join(INPUT_DIR, "lda_outputs")

os.makedirs(OUTPUT_DIR, exist_ok=True)


stop_words = set(stopwords.words("english"))
custom_stopwords = {
    "jeju", "place", "really", "also", "very", "one",
    "would", "could", "get", "got", "went", "go", "come", "back",
    "nice", "good", "great", "amazing", "beautiful", "well",
    "tour", "travel", "visitor", "visitors"
}
stop_words = stop_words.union(custom_stopwords)

lemmatizer = WordNetLemmatizer()

def clean_text(text: str):
    if pd.isna(text):
        return []

    text = str(text).lower()

    # 영어만 남기기
    text = re.sub(r"[^a-z\s]", " ", text)

    tokens = text.split()

    # 길이 3 이상 + 불용어 제거 + 표제어 추출
    tokens = [
        lemmatizer.lemmatize(token)
        for token in tokens
        if token not in stop_words and len(token) >= 3
    ]

    return tokens

def load_all_files(input_dir):
    all_dfs = []

    csv_files = glob.glob(os.path.join(input_dir, "*.csv"))
    xlsx_files = glob.glob(os.path.join(input_dir, "*.xlsx"))

    for file_path in csv_files:
        try:
            df = pd.read_csv(file_path, encoding="utf-8-sig")
        except:
            df = pd.read_csv(file_path, encoding="cp949")

        df["source_file"] = os.path.basename(file_path)
        all_dfs.append(df)

    for file_path in xlsx_files:
        df = pd.read_excel(file_path)
        df["source_file"] = os.path.basename(file_path)
        all_dfs.append(df)

    if not all_dfs:
        raise FileNotFoundError("입력 폴더에서 csv/xlsx 파일을 찾지 못했습니다.")

    combined = pd.concat(all_dfs, ignore_index=True)
    return combined

df = load_all_files(INPUT_DIR)



required_cols = ["id", "review", "address"]
for col in required_cols:
    if col not in df.columns:
        raise ValueError(f"'{col}' 컬럼이 없습니다. 현재 컬럼: {list(df.columns)}")

df = df[required_cols + [col for col in df.columns if col not in required_cols]].copy()

# review 결측 제거
df = df.dropna(subset=["review"]).reset_index(drop=True)


# 텍스트 전처리
df["tokens"] = df["review"].apply(clean_text)

# 토큰 너무 적은 리뷰 제거
df = df[df["tokens"].apply(len) >= 3].reset_index(drop=True)



dictionary = corpora.Dictionary(df["tokens"])

# 너무 드문 단어, 너무 흔한 단어 제거
dictionary.filter_extremes(no_below=5, no_above=0.5)

corpus = [dictionary.doc2bow(tokens) for tokens in df["tokens"]]

# 빈 문서 제거
valid_idx = [i for i, bow in enumerate(corpus) if len(bow) > 0]
df = df.iloc[valid_idx].reset_index(drop=True)
corpus = [corpus[i] for i in valid_idx]


NUM_TOPICS = 6

lda_model = LdaModel(
    corpus=corpus,
    id2word=dictionary,
    num_topics=NUM_TOPICS,
    random_state=42,
    passes=20,
    iterations=400,
    alpha="auto",
    eta="auto"
)

# 토픽별 주요 단어 출력
print("\n===== Topic Keywords =====")
topic_label_map = {}

for topic_id in range(NUM_TOPICS):
    words = lda_model.show_topic(topic_id, topn=10)
    keywords = ", ".join([word for word, prob in words])
    print(f"Topic {topic_id + 1}: {keywords}")
    topic_label_map[topic_id] = keywords


# 각 리뷰의 대표 토픽 부여
def get_dominant_topic(bow):
    topic_probs = lda_model.get_document_topics(bow)
    if not topic_probs:
        return None, None
    dominant_topic, prob = max(topic_probs, key=lambda x: x[1])
    return dominant_topic, prob

dominant_topics = []
topic_probs = []

for bow in corpus:
    topic_id, prob = get_dominant_topic(bow)
    dominant_topics.append(topic_id)
    topic_probs.append(prob)

df["dominant_topic"] = [t + 1 if t is not None else None for t in dominant_topics]
df["topic_probability"] = topic_probs
df["topic_keywords"] = [topic_label_map[t] if t is not None else None for t in dominant_topics]


# keyword 붙이기
manual_keyword_map = {
    1: "topic1",
    2: "topic2",
    3: "topic3",
    4: "topic4"
}

df["keyword"] = df["dominant_topic"].map(manual_keyword_map)


# 전체 결과 저장
all_output_path = os.path.join(OUTPUT_DIR, "all_reviews_with_topics.csv")
df.to_csv(all_output_path, index=False, encoding="utf-8-sig")


# 토픽별 파일 저장
for topic_num in sorted(df["dominant_topic"].dropna().unique()):
    topic_df = df[df["dominant_topic"] == topic_num].copy()
    save_path = os.path.join(OUTPUT_DIR, f"topic_{int(topic_num)}_reviews.csv")
    topic_df.to_csv(save_path, index=False, encoding="utf-8-sig")


# 주소 기준 집계 파일 생성
address_topic_summary = (
    df.groupby(["address", "keyword"])
      .size()
      .reset_index(name="review_count")
      .sort_values(["keyword", "review_count"], ascending=[True, False])
)

summary_path = os.path.join(OUTPUT_DIR, "address_keyword_summary.csv")
address_topic_summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

print("\n===== 저장 완료 =====")
print(f"전체 결과: {all_output_path}")
print(f"주소-키워드 집계: {summary_path}")
print(f"토픽별 파일: {OUTPUT_DIR}")