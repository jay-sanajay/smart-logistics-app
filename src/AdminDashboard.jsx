import { useEffect, useState } from "react";
import { API_BASE } from "./constants";
import "./admin.css";
function AdminDashboard({ token }) {
  const [driverRoutes, setDriverRoutes] = useState([]);

  useEffect(() => {
    const fetchRoutes = async () => {
      try {
        const res = await fetch(`${API_BASE}/admin/drivers`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        const data = await res.json();
        setDriverRoutes(data);
      } catch (err) {
        console.error("Failed to fetch driver routes:", err);
      }
    };
    fetchRoutes();
  }, [token]);

return (
  <div className="admin-dashboard">
    <h2>🛠️ Admin Dashboard</h2>
    <div className="table-container">
      <table className="admin-table">
        <thead>
          <tr>
            <th>Route ID</th>
            <th>Driver Name</th>
            <th>Optimal Path</th>
            <th>Time (mins)</th>
            <th>Distance (km)</th>
          </tr>
        </thead>
        <tbody>
          {driverRoutes.map((route, index) => {
            let formattedPath = "N/A";

            if (Array.isArray(route.path)) {
              formattedPath = route.path
                .map((p) =>
                  typeof p === "string"
                    ? p
                    : p?.place_name || JSON.stringify(p)
                )
                .join(" ➡️ ");
            } else if (typeof route.path === "string") {
              try {
                const parsed = JSON.parse(route.path);
                if (Array.isArray(parsed)) {
                  formattedPath = parsed
                    .map((p) =>
                      typeof p === "string"
                        ? p
                        : p?.place_name || JSON.stringify(p)
                    )
                    .join(" ➡️ ");
                } else {
                  formattedPath = route.path;
                }
              } catch (err) {
                formattedPath = route.path;
              }
            }

            return (
              <tr key={index}>
                <td>{route.route_id || "N/A"}</td>
                <td>{route.driver_name || "N/A"}</td>
                <td>{formattedPath}</td>
                <td>{route.duration_min ?? "N/A"}</td>
                <td>{route.distance_km ?? "N/A"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  </div>
);

}

export default AdminDashboard;
