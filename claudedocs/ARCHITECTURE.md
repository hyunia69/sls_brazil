# VLibras Three.js Player - Architecture Document

## 1. 프로젝트 개요

브라질 수어(LIBRAS) 모션 데이터를 Three.js로 재생하는 웹 플레이어.
VLibras 시스템의 Unity AssetBundle 데이터를 파싱하여 3D 아바타에 적용한다.

### 1.1 목표
- Unity AssetBundle → JSON 추출 파이프라인
- Three.js FBX 아바타 로딩 및 애니메이션 재생
- 다양한 수어 단어의 순차 재생
- 다중 아바타 모델 지원

### 1.2 기술 스택
- **렌더링**: Three.js (v0.162.0+), WebGL
- **아바타 로딩**: FBXLoader (점/대시 포함 본 이름 보존)
- **전처리**: Python + UnityPy (AssetBundle 추출)
- **실행**: 정적 HTML, `python -m http.server`

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────┐
│                 오프라인 파이프라인                  │
│                                                   │
│  Unity AssetBundle ──→ Python/UnityPy ──→ JSON   │
│  (.data file)         extract_animation.py        │
└────────────────────────────┬──────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────┐
│                  웹 플레이어                       │
│                                                   │
│  ┌──────────────┐    ┌──────────────────┐        │
│  │  FBXLoader    │    │  JSON Loader      │        │
│  │  (아바타)     │    │  (애니메이션)     │        │
│  └──────┬───────┘    └──────┬───────────┘        │
│         │                    │                     │
│         ▼                    ▼                     │
│  ┌──────────────┐    ┌──────────────────┐        │
│  │  Bone Map     │    │  Clip Builder     │        │
│  │  Construction │    │  (AnimationClip)  │        │
│  └──────┬───────┘    └──────┬───────────┘        │
│         │                    │                     │
│         ▼                    ▼                     │
│  ┌──────────────────────────────────────┐        │
│  │  Bind Pose Calibration               │        │
│  │  (frame-0 적용 + calculateInverses)  │        │
│  └──────────────┬───────────────────────┘        │
│                  │                                 │
│                  ▼                                 │
│  ┌──────────────────────────────────────┐        │
│  │  AnimationMixer                       │        │
│  │  (재생, 일시정지, 속도 제어)          │        │
│  └──────────────┬───────────────────────┘        │
│                  │                                 │
│                  ▼                                 │
│  ┌──────────────────────────────────────┐        │
│  │  WebGL Renderer                       │        │
│  │  (SkinnedMesh + Skeleton)            │        │
│  └──────────────────────────────────────┘        │
└─────────────────────────────────────────────────┘
```

## 3. 핵심 컴포넌트

### 3.1 AssetBundle Extractor (`tools/extract_animation.py`)
- **입력**: Unity AssetBundle 바이너리 (UnityFS 포맷)
- **출력**: JSON (rotation/position/scale/float curves + tangent data)
- **라이브러리**: UnityPy
- **기능**: 단일 파일 추출, 배치 모드, 30FPS 프리베이크

### 3.2 Avatar Loader
- **입력**: FBX 파일 (Icaro/Hozana/Guga)
- **로더**: Three.js FBXLoader
- **핵심**: 본 이름 그대로 보존 (Blender GLB 변환 불필요)
- **텍스처**: 별도 Textures/ 디렉토리에서 로드

### 3.3 Animation Clip Builder
- **입력**: CASA_full.json 형식의 애니메이션 데이터
- **처리**:
  1. bone path에서 leaf name 추출
  2. IK/FK 보조 본 필터링
  3. 좌표 변환 적용 (configurable)
  4. QuaternionKeyframeTrack 생성
- **출력**: THREE.AnimationClip

### 3.4 Bind Pose Calibrator
- **문제**: 아바타의 bind pose ≠ 애니메이션의 reference pose
- **해결**: frame-0를 적용 후 `skeleton.calculateInverses()` 호출
- **중요도**: ★★★ (이전 실패의 핵심 원인)

### 3.5 Playback Controller
- **AnimationMixer**: Three.js 내장 애니메이션 시스템 활용
- **순차 재생**: 단어별 AnimationClip 체이닝
- **전환 효과**: `crossFadeTo()` 블렌딩
- **UI**: 재생/정지, 타임라인, 속도, 프레임 탐색

## 4. 데이터 플로우

### 4.1 오프라인 (1회)
```
1. VLibras CDN에서 AssetBundle 다운로드
   GET dicionario2.vlibras.gov.br/2018.3.1/WEBGL/{WORD}

2. Python UnityPy로 AnimationClip 추출
   python extract_animation.py CASA --prebake --fps 30

3. JSON 저장
   → animations/CASA_full.json
```

### 4.2 런타임
```
1. FBXLoader로 아바타 로드
   → THREE.Group (SkinnedMesh + Skeleton)

2. JSON 애니메이션 fetch
   → parsed object

3. Bone Map 구축
   → {boneName: THREE.Bone}

4. AnimationClip 빌드
   → THREE.AnimationClip

5. Bind Pose 보정
   → skeleton.calculateInverses()

6. 재생
   → mixer.clipAction(clip).play()
```

## 5. 디렉토리 구조

```
vlibras/
├── player/                    # 메인 플레이어
│   └── index.html             # Three.js 플레이어 (단일 파일)
├── tools/                     # 유틸리티
│   └── extract_animation.py   # AssetBundle → JSON 추출기
├── animations/                # 프리추출 JSON 애니메이션
│   └── CASA_full.json
├── avatars/
│   ├── vlibras/               # VLibras FBX 아바타 (PRIMARY)
│   │   ├── icaro/             # Icaro avatar + textures
│   │   ├── hozana/            # Hozana avatar + textures
│   │   ├── guga/              # Guga avatar + textures
│   │   └── index.html         # FBX 뷰어 (참조)
│   ├── avatarModel/           # ABNT 스펙 아바타 (REFERENCE)
│   │   ├── model_external.gltf
│   │   └── *.png textures
│   └── pcmodel/               # LG PC 모델 (REFERENCE)
│       └── Reah_v1.1.glb
├── data/
│   └── CASA/                  # 원본 AssetBundle
│       └── CASA
├── vlibras-portal/            # VLibras 공식 포털 (REFERENCE)
│   ├── app/target/            # Unity WebGL 빌드
│   ├── sample/CASA_extracted/ # 추출된 샘플 데이터
│   └── scripts/               # Python 유틸리티
└── claudedocs/                # 프로젝트 문서
    ├── ARCHITECTURE.md        # 이 파일
    ├── DATA_FORMAT_ANALYSIS.md
    ├── BONE_MAPPING.md
    ├── PREVIOUS_ATTEMPTS.md
    └── IMPLEMENTATION_PLAN.md
```

## 6. VLibras 원본 시스템 참조

### 6.1 포털 구조
- **Widget**: `vlibras-plugin.js` + `.chunk.js` (Webpack 번들)
- **플레이어**: Unity WebGL (13.7MB WASM 빌드)
- **아바타**: Icaro, Hozana, Guga (Unity 내장)
- **번역 API**: `traducao2.vlibras.gov.br/translate`
- **사전 CDN**: `dicionario2.vlibras.gov.br/bundles`

### 6.2 원본 재생 방식
1. 텍스트 → POST /translate → 글로스 문자열
2. 글로스 → GET /bundles → AssetBundle
3. AssetBundle → Unity AnimationClip → 아바타 재생
4. 30 FPS, Legacy AnimationSystem
5. 단어별 순차 재생, 복합어(`&`) 단일 재생

### 6.3 우리의 접근과의 차이
| 항목 | VLibras 원본 | 우리 플레이어 |
|------|-------------|-------------|
| 엔진 | Unity WebGL (WASM) | Three.js |
| 크기 | 13.7MB 초기 로드 | ~1MB (FBX + JS) |
| 아바타 포맷 | Unity 내장 | FBX (FBXLoader) |
| 애니메이션 포맷 | AssetBundle (runtime) | JSON (프리추출) |
| 번들 파싱 | Unity 내장 | Python UnityPy |
