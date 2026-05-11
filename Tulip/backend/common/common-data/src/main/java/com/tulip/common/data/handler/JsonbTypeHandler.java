package com.tulip.common.data.handler;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.ibatis.type.BaseTypeHandler;
import org.apache.ibatis.type.JdbcType;
import org.apache.ibatis.type.MappedJdbcTypes;
import org.apache.ibatis.type.MappedTypes;
import org.postgresql.util.PGobject;

import java.sql.CallableStatement;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

/**
 * PostgreSQL JSONB 컬럼과 Jackson {@link JsonNode} 간 매핑 TypeHandler.
 *
 * <p>KORMARC 서브필드(JSONB), Outbox payload, policy rule 등 JSONB 컬럼에 사용된다.
 * (10_dba/01 §10 KORMARC 하이브리드 모델 참조).</p>
 */
@MappedJdbcTypes(JdbcType.OTHER)
@MappedTypes(JsonNode.class)
public class JsonbTypeHandler extends BaseTypeHandler<JsonNode> {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Override
    public void setNonNullParameter(PreparedStatement ps, int i, JsonNode parameter, JdbcType jdbcType)
            throws SQLException {
        try {
            PGobject pg = new PGobject();
            pg.setType("jsonb");
            pg.setValue(MAPPER.writeValueAsString(parameter));
            ps.setObject(i, pg);
        } catch (JsonProcessingException e) {
            throw new SQLException("JSONB 직렬화 실패", e);
        }
    }

    @Override
    public JsonNode getNullableResult(ResultSet rs, String columnName) throws SQLException {
        return parse(rs.getString(columnName));
    }

    @Override
    public JsonNode getNullableResult(ResultSet rs, int columnIndex) throws SQLException {
        return parse(rs.getString(columnIndex));
    }

    @Override
    public JsonNode getNullableResult(CallableStatement cs, int columnIndex) throws SQLException {
        return parse(cs.getString(columnIndex));
    }

    private JsonNode parse(String value) throws SQLException {
        if (value == null) {
            return null;
        }
        try {
            return MAPPER.readTree(value);
        } catch (JsonProcessingException e) {
            throw new SQLException("JSONB 역직렬화 실패", e);
        }
    }
}
