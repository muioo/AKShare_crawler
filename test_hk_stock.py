"""
测试港股数据获取功能
"""
import akshare as ak


def test_hk_spot():
    """测试港股实时行情"""
    print("正在获取港股实时行情...")
    try:
        df = ak.stock_hk_spot()
        print(f"获取成功！共 {len(df)} 条数据")
        print("\n前5条数据：")
        print(df.head())
        print("\n列名：")
        print(df.columns.tolist())
        return df
    except Exception as e:
        print(f"获取失败: {e}")
        return None


if __name__ == '__main__':
    df = test_hk_spot()
    if df is not None:
        print("\n✅ 港股数据获取测试成功！")
