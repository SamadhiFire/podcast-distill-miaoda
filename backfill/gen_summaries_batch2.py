import json
import os

BACKFILL_DIR = os.path.dirname(os.path.abspath(__file__))


def write_summary(video_id, data):
    path = os.path.join(BACKFILL_DIR, "items", "youtube", video_id, "summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Written: {path}")


# Video 1: 1M3Vdl6DRkU - Lex Fridman Podcast #497 Don Lincoln
summary1 = {
    "schema_version": 1,
    "item_id": "youtube:1M3Vdl6DRkU",
    "platform": "youtube",
    "platform_id": "1M3Vdl6DRkU",
    "transcript_sha256": "7002b6936fc8bb906ee59676523403eab652d1ae8ee59cd771a34b9e1aa91254",
    "metadata": {
        "item_id": "youtube:1M3Vdl6DRkU",
        "platform": "youtube",
        "platform_id": "1M3Vdl6DRkU",
        "source_id": "yt_lex_fridman",
        "source_name": "Lex Fridman",
        "category": "文化 / 社会 / 人文",
        "title": "Biggest Mysteries in Physics: Antimatter, Dark Energy & ToE - Don Lincoln | Lex Fridman Podcast #497",
        "url": "https://www.youtube.com/watch?v=1M3Vdl6DRkU",
        "published_at": "2026-05-29T16:18:31+00:00",
        "report_date": "2026-05-30",
        "duration_seconds": 10423,
        "language": "en"
    },
    "generation": {
        "script": "trae_agent",
        "model": "trae_agent",
        "quality": "trae_agent_validated"
    },
    "digest": {
        "short_title": "物理学最大谜团：反物质、暗能量与万物理论",
        "one_liner": "粒子物理学家深入解读宇宙最深层的未解之谜",
        "why_it_matters": "理解物理学前沿谜题的最佳入门内容，涵盖从统一场到反物质不对称的全景视角",
        "summary": [
            "费米实验室粒子物理学家Don Lincoln以物理学的统一史为线索，从牛顿统一天上与地面引力、麦克斯韦统一电与磁、爱因斯坦的时空统一，一直讲到电弱统一理论，展现了物理学数百年来「将看似无关的现象纳入同一框架」的核心方法论。",
            "关于希格斯玻色子，Lincoln回忆了2012年7月4日发现时费米实验室与CERN的竞争，并解释了希格斯场如何赋予基本粒子质量。他强调希格斯玻色子是标准模型的最后一块拼图，但它的重要性不及爱因斯坦相对论那样改变世界观的突破。",
            "在反物质部分，他详细讲解了费米实验室每2.3秒产出约1亿个反质子的生产速率，以及全球每年仅生产1纳克反物质的现实。他还解释了CERN的ALPHA实验证明反物质在引力作用下向下掉落，强度约为正物质的75%（加减误差后一致）。",
            "关于暗能量，Lincoln解释了1998年宇宙加速膨胀的发现如何揭示了一种排斥性引力的存在。他指出量子场论对真空能量的预测与实际观测相差10的120次方倍，这是「物理学史上最糟糕的预测」。他还讨论了中微子振荡实验可能揭示物质与反物质不对称的奥秘。"
        ],
        "core_points": [
            "物理学的历史本质上是一部统一史：从牛顿统一天上和地面引力开始，每次突破都是将看似无关的现象纳入同一框架",
            "希格斯玻色子是标准模型的终结篇章而非新篇章的开始；它验证了已知理论但未开启新物理",
            "反物质生产极其困难：全球每年仅生产1纳克，制造1克需要10亿年，但它与物质湮灭时释放的能量极为巨大",
            "宇宙中物质与反物质的不对称是最深刻的未解之谜：每十亿亿个反物质粒子对应十亿零一个物质粒子，这微小差异造就了我们",
            "暗能量是引力的排斥形式，驱动宇宙加速膨胀；量子场论对其密度的预测与观测相差10的120次方倍",
            "弦论虽美丽但未被验证：统一能量尺度比当今最强加速器高出10的15次方倍，实验验证可能需要数百年"
        ],
        "key_facts": [
            {
                "label": "反物质年产量",
                "value": "1纳克",
                "context": "全球加速器每年生产的反物质总量，制造1克需要10亿年",
                "source_refs": ["transcript"]
            },
            {
                "label": "希格斯玻色子发现日期",
                "value": "2012年7月4日",
                "context": "CERN大型强子对撞机宣布发现与希格斯玻色子一致的粒子",
                "source_refs": ["transcript"]
            },
            {
                "label": "暗能量预测偏差",
                "value": "10的120次方倍",
                "context": "量子场论预测的真空能量密度与实际观测值的差距，被称为物理学史上最糟糕的预测",
                "source_refs": ["transcript"]
            },
            {
                "label": "反物质引力实验结果",
                "value": "75%强度",
                "context": "CERN的ALPHA实验测得反物质下落加速度约为正物质的75%，误差范围内与100%一致",
                "source_refs": ["transcript"]
            },
            {
                "label": "物质与反物质不对称比",
                "value": "十亿零1比十亿",
                "context": "早期宇宙中每十亿亿个反物质粒子对应十亿零一个物质粒子，湮灭后剩余的就是我们",
                "source_refs": ["transcript"]
            },
            {
                "label": "费米实验室反质子产率",
                "value": "每2.3秒约1亿个",
                "context": "每2.3秒将10的13次方个质子撞入靶材料，产生约1亿个反质子",
                "source_refs": ["transcript"]
            }
        ],
        "takeaways": [
            "基础研究虽看似抽象，但历史上每次统一突破都在百年后彻底改变了人类文明，从电磁学到核能均如此",
            "物理学的终极理论可能还需要数百年才能完成，但当前的未解之谜本身就是最引人入胜的科学前沿"
        ],
        "guests": ["Don Lincoln（费米实验室粒子物理学家）"],
        "topics": ["粒子物理学", "宇宙学", "统一场论"],
        "tensions": [
            "弦论的美丽数学与其无法被实验验证之间的紧张关系",
            "量子场论对真空能量的预测与实际观测相差120个数量级，暴露了理论的深层缺陷",
            "物质与反物质的不对称机制未知，现有理论无法完全解释为什么宇宙由物质而非反物质组成"
        ],
        "quote": {
            "text": "If you are not confused, you are not doing your job.",
            "translation": "如果你没有感到困惑，说明你没有做好你的工作。",
            "kind": "paraphrase",
            "speaker": "Don Lincoln"
        },
        "importance_score": 4,
        "content_density": "high",
        "quality": "trae_agent_validated"
    }
}

write_summary("1M3Vdl6DRkU", summary1)


# Video 2: 1qbRYP-sgko - Cannonball with Wesley Morris
summary2 = {
    "schema_version": 1,
    "item_id": "youtube:1qbRYP-sgko",
    "platform": "youtube",
    "platform_id": "1qbRYP-sgko",
    "transcript_sha256": "3f11780728d4ec2a0dbfba4b650a7453759864d9033b1be0f86ed22bd35a7bde",
    "metadata": {
        "item_id": "youtube:1qbRYP-sgko",
        "platform": "youtube",
        "platform_id": "1qbRYP-sgko",
        "source_id": "yt_cannonball",
        "source_name": "Cannonball with Wesley Morris",
        "category": "文化 / 社会 / 人文",
        "title": "Has the Working Class Gone Out of Style? | On 'The Devil Wears Prada 2' and More",
        "url": "https://www.youtube.com/watch?v=1qbRYP-sgko",
        "published_at": "2026-05-14T12:55:00+00:00",
        "report_date": "2026-05-15",
        "duration_seconds": 682,
        "language": "en"
    },
    "generation": {
        "script": "trae_agent",
        "model": "trae_agent",
        "quality": "trae_agent_validated"
    },
    "digest": {
        "short_title": "工人阶级在流行文化中消失了吗",
        "one_liner": "从《穿普拉达的女王2》看工人形象在影视中的衰退",
        "why_it_matters": "当流行文化越来越聚焦于富豪和CEO，普通劳动者的生活正在被影视叙事遗忘",
        "summary": [
            "Wesley Morris从《穿普拉达的女王2》中一个叫Mac的普通工人角色出发，发现这个穿着旧球帽、胸前口袋插满笔的男人与时尚杂志世界格格不入，引发了他对美国流行文化中工人阶级形象消失的思考。",
            "他回顾了上世纪70年代Norman Lear的电视宇宙（《All in the Family》《Good Times》等），那时劳动是骄傲的来源，失业是家庭最大的恐惧。80年代工厂关闭，叙事转向写字楼和企业阴谋，到了2008年《钢铁侠》标志着科技天才亿万富翁正式成为流行文化的主角。",
            "Morris认为当下需要一场「革命」，让建筑工人、外卖骑手、网约车司机和咖啡师重新成为影视叙事的主角，展现普通劳动者在不确定性中依然保持幽默和尊严的生活。"
        ],
        "core_points": [
            "美国流行文化曾经以工人阶级为核心叙事对象，从马龙·白兰度的码头工人到70年代电视剧中的蓝领家庭",
            "80年代开始叙事重心从工厂转向写字楼，《华尔街》和《工作女郎》等电影把企业阴谋美化为上升通道",
            "2008年《钢铁侠》标志着科技亿万富翁正式取代工人成为流行文化的英雄原型",
            "当代影视作品越来越多地聚焦于老板和拥有者，而非实际做工作的人，这是一种文化层面的缺失",
            "流行文化需要一场「革命」，让外卖骑手、网约车司机等当代劳动者重新成为叙事主角"
        ],
        "key_facts": [
            {
                "label": "《穿普拉达的女王》第一部与续集间隔",
                "value": "20年",
                "context": "Miranda Priestly角色首次出现于2006年，续集在20年后上映",
                "source_refs": ["transcript"]
            }
        ],
        "takeaways": [
            "流行文化中工人形象的消失不仅是审美问题，更反映了社会对中产阶级生活方式的遗忘",
            "影视创作者应当重新将镜头对准普通劳动者，展现他们在不确定性中的生活与尊严"
        ],
        "guests": [],
        "topics": ["流行文化", "工人阶级", "影视叙事"],
        "tensions": [
            "影视作品越来越多聚焦于老板和亿万富翁，而非实际做工作的人",
            "经典工人形象的衰退与中产阶级信念的弱化形成互为因果的循环"
        ],
        "quote": {
            "text": "Popular art about work has always been a kind of fantasy of what is possible.",
            "translation": "关于工作的流行艺术向来都是对可能性的一种幻想。",
            "kind": "paraphrase",
            "speaker": "Wesley Morris"
        },
        "importance_score": 3,
        "content_density": "brief",
        "quality": "trae_agent_validated"
    }
}

write_summary("1qbRYP-sgko", summary2)


# Video 3: 2MF6tqyhS9g - Mishal Husain Show with Ada Ferrer
summary3 = {
    "schema_version": 1,
    "item_id": "youtube:2MF6tqyhS9g",
    "platform": "youtube",
    "platform_id": "2MF6tqyhS9g",
    "transcript_sha256": "ddd03bf2a200a982cba4c4444f3612a64c84ac1b2f95e94be0c42b42a8411856",
    "metadata": {
        "item_id": "youtube:2MF6tqyhS9g",
        "platform": "youtube",
        "platform_id": "2MF6tqyhS9g",
        "source_id": "yt_mishal_husain",
        "source_name": "The Mishal Husain Show",
        "category": "新闻 / 时评 / 全球议题",
        "title": "Cuba on the Brink: Ada Ferrer on Life Under US Pressure | The Mishal Husain Show",
        "url": "https://www.youtube.com/watch?v=2MF6tqyhS9g",
        "published_at": "2026-05-29T05:10:31+00:00",
        "report_date": "2026-05-30",
        "duration_seconds": 2415,
        "language": "en"
    },
    "generation": {
        "script": "trae_agent",
        "model": "trae_agent",
        "quality": "trae_agent_validated"
    },
    "digest": {
        "short_title": "古巴危机：美国压力下的岛屿生存",
        "one_liner": "普利策奖历史学家讲述古巴危机与家族离散的双重故事",
        "why_it_matters": "古巴正面临每天20小时停电的人道主义危机，石油禁运被历史学家称为「集体惩罚」",
        "summary": [
            "普利策奖历史学家Ada Ferrer在新书《Keeper of My Kin》中以自己家族的离散经历为线索，讲述古巴与美国之间超过六十年的复杂关系。她的母亲在1963年带着10个月大的她离开古巴，却被迫留下了9岁半的哥哥，这个分离持续了16年。",
            "Ferrer描述了古巴当前的深层危机：委内瑞拉石油供应中断、墨西哥停止出口石油，导致古巴即使在哈瓦那也面临每天20到22小时的停电。她直言石油禁运是「残忍的集体惩罚」，医院无法运行保暖箱和透析机，救护车没有燃料。",
            "在政治层面，Ferrer批评古巴政府惯于将一切困难归咎于美国禁运，呼吁古巴超越这一「反复使用的台词」，开启全国对话。她还讨论了Marco Rubio的古巴裔背景及其对古政策的影响，以及古巴近年流失约20%人口的大规模移民潮。"
        ],
        "core_points": [
            "古巴当前面临深刻的人道主义危机：每天20到22小时停电，医院无法运行基本设备，石油禁运被称为「集体惩罚」",
            "古巴革命最初并非共产主义运动，而是反独裁、反腐败的民主运动，在美古对抗中逐渐转向社会主义",
            "古巴近年流失了约20%的人口，这是古巴历史上最大规模的移民潮，移民的离别与等待已成为古巴日常生活的一部分",
            "Ferrer家族的离散故事是古美关系的缩影：她同母异父的哥哥在古巴等待16年才与母亲重聚，且在美国的生活也并不顺利",
            "古巴政府和美国政府双方都困在旧有的对抗叙事中，受害的是普通古巴民众的基本生存权利"
        ],
        "key_facts": [
            {
                "label": "古巴每日停电时长",
                "value": "20到22小时",
                "context": "即使在首都哈瓦那，停电也达到每天20到22小时，乡村地区更为严重",
                "source_refs": ["transcript"]
            },
            {
                "label": "古巴近年人口流失",
                "value": "约20%",
                "context": "过去5到10年间古巴失去了约20%的人口，是古巴历史上最大规模的移民潮",
                "source_refs": ["transcript"]
            },
            {
                "label": "马列尔船民潮人数",
                "value": "125000人",
                "context": "1980年马列尔船民潮中，12.5万古巴人在几个月内乘船离开，Ferrer的哥哥即在其中",
                "source_refs": ["transcript"]
            },
            {
                "label": "Ferrer离开古巴年龄",
                "value": "10个月",
                "context": "Ada Ferrer在1963年10个月大时被母亲带离古巴，对古巴没有任何记忆",
                "source_refs": ["transcript"]
            },
            {
                "label": "兄弟分离时长",
                "value": "16年",
                "context": "Ferrer同母异父的哥哥在古巴等待了16年才与母亲重聚，到美国时已经26岁",
                "source_refs": ["transcript"]
            }
        ],
        "takeaways": [
            "石油禁运作为地缘政治工具对普通民众造成的伤害远超其对政府的压力效果，应重新审视其人道主义影响",
            "理解古巴需要超越简单的冷战叙事，既要看到美国禁运的伤害，也要承认古巴政府自身的经济决策失误和压制"
        ],
        "guests": ["Ada Ferrer（普利策奖历史学家，研究古巴与美国关系史）"],
        "topics": ["古美关系", "古巴危机", "移民与离散"],
        "tensions": [
            "美国石油禁运与古巴政府经济失误共同造成了当前的人道危机，双方均回避自身责任",
            "古巴裔美国人对Trump移民政策的不满正在改变佛罗里达州的政治版图",
            "历史学家的个人家族史与其客观学术立场之间的张力"
        ],
        "quote": {
            "text": "The oil embargo is cruel and unjust. It is collective punishment. Hospitals cannot run incubators or dialysis machines.",
            "translation": "石油禁运是残忍且不义的。这是集体惩罚。医院无法运行保暖箱和透析机。",
            "kind": "paraphrase",
            "speaker": "Ada Ferrer"
        },
        "importance_score": 4,
        "content_density": "high",
        "quality": "trae_agent_validated"
    }
}

write_summary("2MF6tqyhS9g", summary3)

print("All 3 summary.json files written successfully.")
