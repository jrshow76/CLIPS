package com.shelfy.common.mybatis;

import org.apache.ibatis.type.BaseTypeHandler;
import org.apache.ibatis.type.JdbcType;
import org.apache.ibatis.type.MappedTypes;

import java.sql.*;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;

@MappedTypes(LocalDateTime.class)
public class TimestamptzTypeHandler extends BaseTypeHandler<LocalDateTime> {

    @Override
    public void setNonNullParameter(PreparedStatement ps, int i, LocalDateTime param, JdbcType jdbcType)
            throws SQLException {
        ps.setObject(i, param.atOffset(ZoneOffset.UTC));
    }

    @Override
    public LocalDateTime getNullableResult(ResultSet rs, String columnName) throws SQLException {
        OffsetDateTime odt = rs.getObject(columnName, OffsetDateTime.class);
        return odt != null ? odt.withOffsetSameInstant(ZoneOffset.UTC).toLocalDateTime() : null;
    }

    @Override
    public LocalDateTime getNullableResult(ResultSet rs, int columnIndex) throws SQLException {
        OffsetDateTime odt = rs.getObject(columnIndex, OffsetDateTime.class);
        return odt != null ? odt.withOffsetSameInstant(ZoneOffset.UTC).toLocalDateTime() : null;
    }

    @Override
    public LocalDateTime getNullableResult(CallableStatement cs, int columnIndex) throws SQLException {
        OffsetDateTime odt = cs.getObject(columnIndex, OffsetDateTime.class);
        return odt != null ? odt.withOffsetSameInstant(ZoneOffset.UTC).toLocalDateTime() : null;
    }
}
