import numpy as np
from scipy.optimize import minimize


def arma(c, phi, theta, r):
    T = len(r)
    epsilon = np.zeros(T)
    for t in range(T):
        if t < len(phi):
            epsilon[t] = r[t] - np.mean(r)
        else:
            ar_sum = np.sum([phi[i] * r[t - 1 - i] for i in range(len(phi))])
            ma_sum = np.sum([theta[i] * epsilon[t - 1 - i] for i in range(len(theta))])
            epsilon[t] = r[t] - c - ar_sum - ma_sum
    return epsilon


def garch(omega, alpha, beta, epsilon):
    T = len(epsilon)
    sigma2 = np.zeros(T)
    for t in range(T):
        if t == 0:
            sigma2[t] = omega / (1 - alpha - beta)  # initialize as unconditional variance
        else:
            sigma2[t] = omega + alpha * epsilon[t - 1] ** 2 + beta * sigma2[t - 1]
    return sigma2


def gjr_garch(omega, alpha, gamma, beta, r, epsilon):
    T = len(epsilon)
    sigma2 = np.zeros(T)

    for t in range(1, T):
        if t == 0:
            sigma2[t] = omega / (1 - alpha - beta)
        else:
            sigma2[t] = omega + alpha * epsilon[t - 1] ** 2 + gamma * r[t - 1] ** 2 * (epsilon[t - 1] < 0) + beta * \
                        sigma2[t - 1]
    return sigma2


def negative_loglikelihood(params, p, q, r, gjr=False):
    T = len(r)
    c = params[0]
    phi = params[1:p + 1]
    theta = params[p + 1:(p + q + 2)]

    if gjr:
        omega = params[-4]
        alpha = params[-3]
        gamma = params[-2]
        beta = params[-1]

        epsilon = arma(c, phi, theta, r)
        sigma2 = gjr_garch(omega, alpha, gamma, beta, r, epsilon)
        sigma2 = np.where(sigma2 <= 0, np.finfo(np.float64).eps, sigma2)
        NegLogL = -0.5 * np.sum(-np.log(sigma2) - epsilon ** 2 / sigma2)

    else:
        omega = params[-3]
        alpha = params[-2]
        beta = params[-1]

        epsilon = arma(c, phi, theta, r)
        sigma2 = garch(omega, alpha, beta, epsilon)
        sigma2 = np.where(sigma2 <= 0, np.finfo(np.float64).eps, sigma2)
        NegLogL = -0.5 * np.sum(-np.log(sigma2) - epsilon ** 2 / sigma2)

    return NegLogL


def order_determination(ts, max_p, max_q, gjr=False, verbose=False, with_fit=True):
    if verbose:
        print('Running Order Determination...')
    finfo = np.finfo(np.float64)
    temp_aic = np.inf
    import warnings
    warnings.filterwarnings("ignore")
    for q in range(1, max_q + 1):
        for p in range(1, max_p + 1):
            # Define bounds for c, phi, theta, omega, alpha, beta
            c_bounds = [(-10 * np.abs(np.mean(ts)), 10 * np.abs(np.mean(ts)))]
            phi_bounds = [(-0.99999999, 0.99999999) for i in range(p)]
            theta_bounds = [(-0.99999999, 0.99999999) for i in range(q)]
            omega_bounds = [(finfo.eps, 2 * np.var(ts))]
            alpha_bounds = [(0.0, 1.0)]
            gamma_bounds = [(0.0, 1.0)]
            beta_bounds = [(0.0, 1.0)]

            if gjr:
                bounds = c_bounds + phi_bounds + theta_bounds + omega_bounds + alpha_bounds + gamma_bounds + beta_bounds
                initial_params = tuple(np.mean(ts) for _ in range(1 + p + q)) + tuple((np.var(ts) * 0.01, .03, .09, .90))

                res = minimize(negative_loglikelihood, initial_params, args=(p, q, ts, True), bounds=bounds,
                               method='SLSQP')
                neg_llh_val = res.fun
                aic = 2 * len(initial_params) + 2 * neg_llh_val
                if aic < temp_aic:
                    best_p = p
                    best_q = q
                    temp_aic = aic
                    if verbose:
                        print('Current best model: ARMA({},{})-GJR-GARCH(1,1,1), AIC = {}'.format(str(p), str(q), temp_aic))

            else:
                bounds = c_bounds + phi_bounds + theta_bounds + omega_bounds + alpha_bounds + beta_bounds

                initial_params = tuple(np.mean(ts) for _ in range(1 + p + q)) + tuple((np.var(ts) * 0.01, .03, .90))

                res = minimize(negative_loglikelihood, initial_params, args=(p, q, ts, False), bounds=bounds,
                               method='SLSQP')
                neg_llh_val = res.fun
                aic = 2 * len(initial_params) + 2 * neg_llh_val
                if aic < temp_aic:
                    best_p = p
                    best_q = q
                    temp_aic = aic
                    if verbose:
                        print('Current best model: ARMA({},{})-GARCH(1,1), AIC = {}'.format(str(p), str(q), temp_aic))

    if with_fit:
        print('Fitting model...')
        phi_bounds = [(-0.99999999, 0.99999999) for i in range(best_p)]
        theta_bounds = [(-0.99999999, 0.99999999) for i in range(best_q)]

        if gjr:
            bounds = c_bounds + phi_bounds + theta_bounds + omega_bounds + alpha_bounds + gamma_bounds + beta_bounds
            initial_params = tuple(np.mean(ts) for _ in range(1 + best_p + best_q)) + tuple((np.var(ts) * 0.01, .03, .09, .90))

            final_res = minimize(negative_loglikelihood, initial_params, args=(best_p, best_q, ts, True), bounds=bounds,
                           method='SLSQP')
        else:
            bounds = c_bounds + phi_bounds + theta_bounds + omega_bounds + alpha_bounds + beta_bounds
            initial_params = tuple(np.mean(ts) for _ in range(1 + best_p + best_q)) + tuple((np.var(ts) * 0.01, .03, .90))

            final_res = minimize(negative_loglikelihood, initial_params, args=(best_p, best_q, ts, False), bounds=bounds,
                           method='SLSQP')

        print('Model fitting complete.')
        return final_res

    else:
        print('Order determination completed.')
        print('p =', best_p)
        print('q =', best_q)
        print('AIC =', temp_aic)