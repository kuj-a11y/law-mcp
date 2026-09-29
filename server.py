import os
import json
import httpx

from mcp.server.mcpserver import MCPServer


# 국가법령정보센터 API 인증키
LAW_OC = os.environ.get("LAW_OC")

if not LAW_OC:
    raise RuntimeError("LAW_OC 환경변수가 설정되지 않았습니다.")


mcp = MCPServer(
    "Korea Law Information",
    instructions=(
        "국가법령정보센터 Open API를 이용해 대한민국 법령정보를 "
        "검색하고 조회하는 MCP 서버입니다. "
        "법령 관련 질문에는 가능한 한 국가법령정보센터의 "
        "공식 API 결과를 우선 사용합니다."
    ),
)


# ---------------------------------------------------------
# 국가법령정보센터 API 호출
# ---------------------------------------------------------

async def call_law_api(endpoint: str, params: dict) -> dict:
    request_params = {
        "OC": LAW_OC,
        "type": "JSON",
        **params,
    }

    url = f"https://www.law.go.kr/DRF/{endpoint}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            url,
            params=request_params,
        )

        response.raise_for_status()

        return response.json()


# ---------------------------------------------------------
# 법령 검색
# ---------------------------------------------------------

@mcp.tool()
async def search_law(
    query: str,
    display: int = 10,
    page: int = 1,
) -> str:
    """
    국가법령정보센터에서 법령을 검색합니다.

    query: 검색할 법령명 또는 검색어
    예: 근로기준법, 산업안전보건법

    display: 검색 결과 개수
    page: 검색 페이지
    """

    display = max(1, min(display, 100))
    page = max(1, page)

    data = await call_law_api(
        "lawSearch.do",
        {
            "target": "law",
            "query": query,
            "display": display,
            "page": page,
            "search": 1,
        },
    )

    return json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
    )


# ---------------------------------------------------------
# 법령 본문 조회
# ---------------------------------------------------------

@mcp.tool()
async def get_law(
    law_id: str,
) -> str:
    """
    국가법령정보센터에서 특정 법령의 본문을 조회합니다.

    law_id: 법령 검색 결과에 표시되는 법령ID
    """

    data = await call_law_api(
        "lawService.do",
        {
            "target": "law",
            "ID": law_id,
        },
    )

    return json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
    )


# ---------------------------------------------------------
# 특정 조문 조회
# ---------------------------------------------------------

@mcp.tool()
async def get_law_article(
    law_id: str,
    article_number: int,
    sub_article_number: int | None = None,
) -> str:
    """
    특정 법령의 특정 조문을 조회합니다.

    예:
    제23조 → article_number=23

    제23조의2 → article_number=23,
                 sub_article_number=2
    """

    if article_number < 1:
        raise ValueError("article_number는 1 이상이어야 합니다.")

    if sub_article_number is None:
        # 제23조 = 002300
        jo = f"{article_number:04d}00"
    else:
        if sub_article_number < 1:
            raise ValueError(
                "sub_article_number는 1 이상이어야 합니다."
            )

        # 제23조의2 = 002302
        jo = f"{article_number:04d}{sub_article_number:02d}"

    data = await call_law_api(
        "lawService.do",
        {
            "target": "law",
            "ID": law_id,
            "JO": jo,
        },
    )

    return json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
    )


# ---------------------------------------------------------
# 특정 시행일의 법령 본문 조회
# ---------------------------------------------------------

@mcp.tool()
async def get_law_at_effective_date(
    law_id: str,
    effective_date: str,
) -> str:
    """
    특정 시행일 기준의 법령 본문을 조회합니다.

    effective_date:
    YYYYMMDD 형식

    예:
    20260101
    """

    if len(effective_date) != 8 or not effective_date.isdigit():
        raise ValueError(
            "effective_date는 YYYYMMDD 형식이어야 합니다."
        )

    data = await call_law_api(
        "lawService.do",
        {
            "target": "eflaw",
            "ID": law_id,
            "efYd": effective_date,
        },
    )

    return json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
    )


# ---------------------------------------------------------
# 서버 실행
# ---------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
        stateless_http=True,
        json_response=True,
    )
