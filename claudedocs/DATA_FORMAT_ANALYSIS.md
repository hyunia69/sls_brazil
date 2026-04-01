# VLibras AssetBundle Data Format Analysis

## 1. Unity AssetBundle 구조

### 1.1 파일 헤더
```
Magic: "UnityFS"
Format Version: 6
Unity Version: 5.x.x (built with 2018.3.1f1)
Bundle ID: CAB-c4452c74c297f4ac972f8ff5920878e6
File Size: 19,719 bytes
```

### 1.2 에셋 구성
| path_id | type | name |
|---------|------|------|
| 1 | AssetBundle | (container) |
| 2021152704087311190 | AnimationClip | CASA |

## 2. AnimationClip 구조

### 2.1 메타데이터
- **name**: "CASA"
- **sample_rate**: 30.0 FPS
- **legacy**: true (Unity Legacy Animation System)
- **compressed**: false
- **high_quality_curve**: true
- **duration**: ~2.467초 (time=0.0 ~ 2.4666666984558105)

### 2.2 Bounds
```json
{
  "center": [-1.478e-05, 1.429, 1.390],
  "extent": [2.167, 4.263, 2.262]
}
```
단위는 Unity 미터. 아바타가 약 4.26m 높이 범위 (2 × extent.y).

### 2.3 Curve 유형 요약
| Curve Type | Count | Description |
|-----------|-------|-------------|
| Rotation (Quaternion) | 5 | 루트 + IK 컨트롤러만 |
| Position (Vector3) | 80+ | 모든 본의 로컬 위치 |
| Scale | 84 | 얼굴/바디 보조 애니메이션 |
| Float | 22 | blend shape/morph target |

**주의**: CASA는 정적 포즈(2 keyframe, 동일 값). 실제 동적 수어 단어는 더 많은 keyframe을 가짐.

## 3. 스켈레톤 계층 구조 (84 Bone Paths)

### 3.1 전체 계층
```
Armature.001 (루트 armature, Rx -90°)
├── BnBacia.001 (pelvis root)
│   ├── BnBacia (hip)
│   │   ├── BnBacia_L → BnPerna.L (왼쪽 다리)
│   │   └── BnBacia_R → BnPerna.R (오른쪽 다리)
│   └── BnCol-01 (척추 1)
│       └── BnCol-02 (척추 2)
│           └── BnCol-03 (척추 3)
│               ├── BnOmbro.L (왼쪽 어깨)
│               │   └── BnBraco.L (왼팔)
│               │       └── BnAntBraco.L (왼 전완)
│               │           └── BnAntBraco.L.001 (왼 전완 보조)
│               │               └── BnMao.L (왼손)
│               │                   ├── BnDedo.1.L (엄지) → .006 → .005
│               │                   ├── BnDedo.1.L.001 (검지) → .008 → .007
│               │                   ├── BnDedo.1.L.002 (중지) → .010 → .009
│               │                   ├── BnDedo.1.L.003 (약지) → .012 → .011
│               │                   └── BnDedo.1.L.004 (소지) → .014 → .013
│               ├── BnOmbro.R (오른쪽 어깨, 대칭)
│               │   └── ... (왼쪽과 동일 구조, .R 접미사)
│               └── BnPescoco (목)
│                   └── BnCabeca (머리)
│                       ├── BnBocaCanto.L/R (입꼬리)
│                       ├── BnBochecha.L/R (볼)
│                       ├── BnDirigeQueixo (턱 방향)
│                       ├── BnLabioCentroInfer (하 입술)
│                       ├── BnLabioCentroSuper (상 입술)
│                       ├── BnMandibula (하악골)
│                       │   └── BnLingua → .003 → .001 → .002 (혀 체인)
│                       ├── BnOlho.L/R (눈)
│                       ├── BnOlhosMira (눈 타겟 부모)
│                       │   ├── BnOlhoMira.L (왼눈 타겟)
│                       │   └── BnOlhoMira.R (오른눈 타겟)
│                       ├── BnPalpebInfe.L/R (하 눈꺼풀)
│                       ├── BnPalpebSuper.L/R (상 눈꺼풀)
│                       ├── BnSobrancCentro (눈썹 중앙)
│                       ├── BnSobrancCentro.L/R (눈썹 중앙 좌/우)
│                       └── BnSobrancLateral.L/R (눈썹 측면)
├── BnMaoOrient.L/R (손 방향 IK 타겟)
├── BnPolyV.L/R (폴 벡터 IK 컨트롤)
└── ik_FK.L/R (IK/FK 블렌드 컨트롤)
```

### 3.2 포르투갈어 본 이름 사전
| Bone Prefix | Portuguese | English | Body Part |
|------------|-----------|---------|-----------|
| BnBacia | Bacia | Pelvis/Hip | 골반 |
| BnCol | Coluna | Spine/Column | 척추 |
| BnOmbro | Ombro | Shoulder | 어깨 |
| BnBraco | Braço | Arm | 팔 |
| BnAntBraco | Antebraço | Forearm | 전완 |
| BnMao | Mão | Hand | 손 |
| BnDedo | Dedo | Finger | 손가락 |
| BnPescoco | Pescoço | Neck | 목 |
| BnCabeca | Cabeça | Head | 머리 |
| BnPerna | Perna | Leg | 다리 |
| BnMandibula | Mandíbula | Mandible/Jaw | 하악골 |
| BnLingua | Língua | Tongue | 혀 |
| BnOlho | Olho | Eye | 눈 |
| BnPalpeb | Pálpebra | Eyelid | 눈꺼풀 |
| BnSobranc | Sobrancelha | Eyebrow | 눈썹 |
| BnBochecha | Bochecha | Cheek | 볼 |
| BnLabio | Lábio | Lip | 입술 |
| BnBocaCanto | Boca Canto | Mouth Corner | 입꼬리 |

### 3.3 보조 본 (IK/FK 컨트롤러)
이 본들은 변형(deformation)에 사용되지 않으며, 애니메이션 리깅용:
- `BnMaoOrient.L/R` - 손 방향 IK 타겟
- `BnPolyV.L/R` - 폴 벡터 (IK 해석의 회전 평면 제어)
- `ik_FK.L/R` - IK/FK 블렌드 팩터

**처리 방침**: 플레이어에서 건너뛰기. FK 결과는 이미 각 변형 본의 rotation curve에 베이크됨.

## 4. Keyframe 데이터 형식

### 4.1 Rotation Curve (Quaternion)
```json
{
  "path": "Armature.001/BnBacia.001/BnCol-01",
  "keyframes": [
    {
      "time": 0.0,
      "value": [x, y, z, w],
      "inSlope": [x, y, z, w],
      "outSlope": [x, y, z, w],
      "inWeight": [x, y, z, w],
      "outWeight": [x, y, z, w],
      "weightedMode": 0
    }
  ]
}
```

Unity의 Quaternion 순서: `(x, y, z, w)` - Three.js와 동일.

### 4.2 Position Curve (Vector3)
```json
{
  "path": "Armature.001/BnBacia.001",
  "keyframes": [
    {
      "time": 0.0,
      "value": [x, y, z]
    }
  ]
}
```

Position 값 범위: 0.001 ~ 0.01 (Unity 미터 단위).
FBX 아바타는 cm 단위일 수 있으므로 scale factor 필요.

### 4.3 Interpolation
Unity AnimationCurve는 Hermite 스플라인 보간:
- `inSlope/outSlope`: tangent (접선 기울기)
- `inWeight/outWeight`: weighted tangent 모드
- `weightedMode`: 0=none, 1=in, 2=out, 3=both

**실용적 접근**: 30FPS 프리베이크 시 linear interpolation으로 충분.

## 5. VLibras 시스템 데이터 플로우

```
사용자 텍스트 선택
    ↓
POST traducao2.vlibras.gov.br/translate {text: "포르투갈어"}
    ↓
응답: "LIBRAS GLOSS 표기" (예: "CASA", "PRESIDENTE BRASIL&PAIS")
    ↓
GET dicionario2.vlibras.gov.br/signs?version=2018.3.1
    ↓
GET dicionario2.vlibras.gov.br/2018.3.1/WEBGL/{WORD}
    ↓
Unity AssetBundle → AnimationClip → 아바타 재생
```

### 5.1 글로스 표기법
- 대문자: 모든 글로스 단어
- `&`: 복합어 (하나의 애니메이션으로 재생)
- `[PONTO]`: 마침표
- `[INTERROGAÇÃO]`: 물음표 (눈썹 올림 + 고개 기울기)
- `_`: 다중 단어 구문
