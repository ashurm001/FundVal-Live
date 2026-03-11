from fastapi import APIRouter, Query, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from typing import Optional
import json
from ..services.data_transfer import data_transfer_service

router = APIRouter()


@router.get("/export/json")
def export_positions_json(account_id: int = Query(1)):
    """
    导出持仓数据为JSON格式

    Args:
        account_id: 账户ID

    Returns:
        JSON格式的持仓数据
    """
    result = data_transfer_service.export_positions_json(account_id)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return JSONResponse(
        content=result,
        headers={
            "Content-Disposition": f"attachment; filename=positions_export_{account_id}.json"
        }
    )


@router.get("/export/csv")
def export_positions_csv(account_id: int = Query(1)):
    """
    导出持仓数据为CSV格式

    Args:
        account_id: 账户ID

    Returns:
        CSV格式的持仓数据
    """
    csv_content, filename = data_transfer_service.export_positions_csv(account_id)

    if not csv_content:
        raise HTTPException(status_code=400, detail=filename)

    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/import/json")
async def import_positions_json(
    file: UploadFile = File(...),
    account_id: int = Query(1),
    merge_strategy: str = Query("replace", description="合并策略: replace(替换)/merge(合并)/skip(跳过重复)")
):
    """
    从JSON文件导入持仓数据

    Args:
        file: JSON文件
        account_id: 目标账户ID
        merge_strategy: 合并策略

    Returns:
        导入结果统计
    """
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Only JSON files are supported")

    try:
        content = await file.read()
        data = json.loads(content)

        result = data_transfer_service.import_positions_json(data, account_id, merge_strategy)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/csv")
async def import_positions_csv(
    file: UploadFile = File(...),
    account_id: int = Query(1),
    merge_strategy: str = Query("replace", description="合并策略: replace(替换)/merge(合并)/skip(跳过重复)")
):
    """
    从CSV文件导入持仓数据

    Args:
        file: CSV文件
        account_id: 目标账户ID
        merge_strategy: 合并策略

    Returns:
        导入结果统计
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    try:
        content = await file.read()
        csv_content = content.decode('utf-8')

        result = data_transfer_service.import_positions_csv(csv_content, account_id, merge_strategy)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
