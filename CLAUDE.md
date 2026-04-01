# VLibras Three.js Player Project

브라질 수어(LIBRAS) 모션 데이터를 Three.js로 재생하는 웹 플레이어.
Unity AssetBundle 형태의 수어 모션 데이터를 FBX 아바타에 적용한다.

## 핵심 전략

**FBXLoader 직접 사용** - Blender GLB 변환 파이프라인을 완전히 우회하여 본 이름 보존 및 좌표계 통일.

## 디렉토리 구조

```
vlibras/
├── player/            # Three.js 플레이어 (구현 예정)
├── tools/             # Python 유틸리티 (추출기)
├── animations/        # 프리추출 JSON 애니메이션
├── avatars/vlibras/   # VLibras FBX 아바타 (Icaro/Hozana/Guga)
├── avatars/avatarModel/ # ABNT 스펙 아바타 (참조)
├── avatars/pcmodel/   # LG PC 모델 (참조)
├── data/CASA/         # 원본 AssetBundle 샘플
├── vlibras-portal/    # VLibras 공식 포털 코드 (참조)
└── claudedocs/        # 프로젝트 문서
```

## 문서 링크

| 문서 | 내용 |
|------|------|
| [ARCHITECTURE.md](claudedocs/ARCHITECTURE.md) | 전체 시스템 아키텍처 |
| [DATA_FORMAT_ANALYSIS.md](claudedocs/DATA_FORMAT_ANALYSIS.md) | AssetBundle/AnimationClip 데이터 포맷 분석 |
| [BONE_MAPPING.md](claudedocs/BONE_MAPPING.md) | 본 매핑, 좌표계, Bind Pose 분석 |
| [PREVIOUS_ATTEMPTS.md](claudedocs/PREVIOUS_ATTEMPTS.md) | 이전 시도 분석 및 교훈 |
| [IMPLEMENTATION_PLAN.md](claudedocs/IMPLEMENTATION_PLAN.md) | 단계별 구현 계획 |

## 기술 스택

- **렌더링**: Three.js (WebGL), FBXLoader
- **전처리**: Python + UnityPy (AssetBundle 추출)
- **데이터**: Unity AnimationClip → JSON (30FPS, Quaternion keyframes)
- **아바타**: FBX (84본, 포르투갈어 본 이름, Bn 접두사)

## 참조 프로젝트

- `D:\lg\work\SLS\brazil\code\player\` - 이전 작업 (ABNT 완료, VLibras 진행중)
- VLibras 번역 API: `traducao2.vlibras.gov.br/translate`
- VLibras 사전 CDN: `dicionario2.vlibras.gov.br/bundles`
