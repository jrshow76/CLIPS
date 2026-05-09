package com.shelfy.item.mapper;

import org.apache.ibatis.type.BaseTypeHandler;
import org.apache.ibatis.type.JdbcType;

import java.sql.*;
import java.util.Arrays;
import java.util.List;

/**
 * PostgreSQL VARCHAR[] 배열 타입 ↔ List<String> 변환 TypeHandler
 * <p>
 * MyBatis는 기본적으로 PostgreSQL 배열 타입을 지원하지 않으므로
 * 커스텀 TypeHandler로 처리한다.
 */
public class StringArrayTypeHandler extends BaseTypeHandler<List<String>> {

    @Override
    public void setNonNullParameter(PreparedStatement ps, int i,
            List<String> parameter, JdbcType jdbcType) throws SQLException {
        Connection conn = ps.getConnection();
        Array array = conn.createArrayOf("VARCHAR", parameter.toArray());
        ps.setArray(i, array);
    }

    @Override
    public List<String> getNullableResult(ResultSet rs, String columnName) throws SQLException {
        return extractArray(rs.getArray(columnName));
    }

    @Override
    public List<String> getNullableResult(ResultSet rs, int columnIndex) throws SQLException {
        return extractArray(rs.getArray(columnIndex));
    }

    @Override
    public List<String> getNullableResult(CallableStatement cs, int columnIndex) throws SQLException {
        return extractArray(cs.getArray(columnIndex));
    }

    private List<String> extractArray(Array array) throws SQLException {
        if (array == null) {
            return List.of();
        }
        String[] strings = (String[]) array.getArray();
        return strings != null ? Arrays.asList(strings) : List.of();
    }
}
