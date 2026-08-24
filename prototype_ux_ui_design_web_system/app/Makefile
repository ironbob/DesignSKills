.PHONY: dev test smoke calibrate

# 一键运行（自检依赖→自动安装→起双服务→自动开浏览器）
dev:            ## 等价于仓库根 start.sh（AI_RUNNER=claude make dev 可真跑）
	bash ../start.sh

test:           ## 后端全量测试（mock 模式，不烧配额）
	cd backend && uv run python -m pytest -q

smoke:          ## 真实冒烟：claude CLI 跑阶段 1（消耗配额，约 1-2 分钟）
	cd backend && ./smoke_stage1.sh

calibrate:      ## 判据卡校准回测：本地金标准跑 L2 评审，🔴 必须为 0（消耗配额；语料自备：make calibrate GOLD=<目录> 或 WB_GOLD_DIR，仓库不内置路径）
	cd backend && uv run python calibrate_rubrics.py $(if $(GOLD),--gold $(GOLD),)
