import { API_BASE } from "./constants";

// ✅ Decode JWT safely
const decodeJWT = (token) => {
  try {
    const base64 = token.split(".")[1];
    const decoded = JSON.parse(atob(base64));
    return decoded;
  } catch (error) {
    console.error("Failed to decode token", error);
    return null;
  }
};

// ✅ Login with JWT + decoded role & username
export const login = async (username, password) => {
  try {
    const res = await fetch(`${API_BASE}/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({ username, password }),
    });

    if (!res.ok) throw new Error("Login failed");

    const data = await res.json(); // { access_token: "..." }
    const decoded = decodeJWT(data.access_token);

    return {
      token: data.access_token,
      role: decoded?.role || "unknown",
      username: decoded?.sub || "",
    };
  } catch (err) {
    alert(err.message);
    return {};
  }
};

// ✅ Signup with role-based registration
export const signup = async (username, password, role = "customer") => {
  try {
    const res = await fetch(`${API_BASE}/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, role }),
    });

    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || "Signup failed");
    }

    const data = await res.json();
    const decoded = decodeJWT(data.access_token);

    return {
      token: data.access_token,
      role: decoded?.role || "unknown",
      username: decoded?.sub || "",
    };
  } catch (err) {
    alert(err.message);
    return {};
  }
};

// ✅ Logout logic
export const logout = (setToken, setIsAdmin) => {
  setToken("");
  if (setIsAdmin) setIsAdmin(false);
  localStorage.removeItem("token");
};
